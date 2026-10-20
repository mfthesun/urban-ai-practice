"""Собирает dashboard.html из готовых GeoJSON и матрицы доступности.

Ничего не скачивает и не пересчитывает метрики.
Запуск:  python dashboard.py
"""

import json
import os

import folium
import geopandas as gpd
import pandas as pd
from branca.colormap import LinearColormap


def find_project_root() -> str:
    for cand in (os.getcwd(), os.path.abspath(os.path.join(os.getcwd(), ".."))):
        if os.path.exists(os.path.join(cand, "pyproject.toml")):
            return cand
    return os.getcwd()


ROOT = find_project_root()
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "dashboard.html")

blocks = gpd.read_file(os.path.join(DATA, "blocks_metrics.geojson"))
schools = gpd.read_file(os.path.join(DATA, "schools.geojson"))
acc_mx = pd.read_pickle(os.path.join(DATA, "accessibility_matrix.pkl"))

if blocks.crs is None:
    blocks = blocks.set_crs("EPSG:32631")

blocks["area_ha"] = blocks.area / 1e4
blocks["median_time_min"] = acc_mx.median(axis=1).reindex(blocks.index)
built = blocks[blocks["footprint_area"] > 0].copy()
g = blocks.to_crs(4326)

population = int(blocks["population"].sum())
capacity = int(blocks["capacity"].sum())
demand = int(blocks["demand"].sum())
fsi_median = round(float(built["fsi"].median()), 2)
gsi_median = round(float(built["gsi"].median()), 2)
walk_median = round(float(blocks["median_time_min"].median()), 1)
walk_max = round(float(blocks["median_time_min"].max()), 0)
deficit_blocks = int((blocks["demand_left"] > 0).sum())
provision_mean = round(float(built["provision_strong"].fillna(0).mean()), 2)
area_ha = round(float(blocks["area_ha"].sum()), 0)


def ru(num: int) -> str:
    return f"{num:,}".replace(",", " ")


# ------------------------------------------------------------------ карта
m = folium.Map(location=[41.3925, 2.1645], zoom_start=14, tiles="CartoDB positron",
               attr="OpenStreetMap · BlocksNet")


def choropleth(column, name, palette, vmin=None, vmax=None, show=False):
    values = g[column].astype(float)
    lo = values.min() if vmin is None else vmin
    hi = values.max() if vmax is None else vmax
    cmap = LinearColormap(palette, vmin=lo, vmax=hi)
    cmap.caption = name

    def style(feature):
        value = feature["properties"].get(column)
        fill = "#e2e8f0" if value is None else cmap(value)
        return {"fillColor": fill, "color": "#4a5568", "weight": 0.3, "fillOpacity": 0.82}

    layer = folium.FeatureGroup(name=name, show=show)
    folium.GeoJson(
        g[["geometry", column]].to_json(),
        style_function=style,
        tooltip=folium.GeoJsonTooltip(fields=[column], aliases=[name]),
    ).add_to(layer)
    layer.add_to(m)


choropleth("fsi", "FSI — интенсивность застройки", ["#f7fbff", "#08306b"])
choropleth("population", "Население (оценка), чел.", ["#fff5eb", "#7f2704"])
choropleth("provision_strong", "Обеспеченность школами, доля", ["#d73027", "#fee08b", "#1a9850"], 0, 1)
choropleth("area_accessibility", "Доступность с учётом площади", ["#ffffcc", "#800026"])
choropleth("median_time_min", "Медианное время пешком, мин", ["#f1eef6", "#045a8d"])

LU_COLORS = {
    "RESIDENTIAL": "#1f78b4", "BUSINESS": "#e31a1c", "RECREATION": "#33a02c",
    "INDUSTRIAL": "#6a3d9a", "SPECIAL": "#ff7f00", "TRANSPORT": "#b15928",
    "AGRICULTURE": "#b2df8a", "None": "#e2e8f0",
}


def lu_key(value) -> str:
    if value is None:
        return "None"
    text = str(value)
    if text in ("None", "nan", ""):
        return "None"
    return text.split(".")[-1].replace("'", "").replace(">", "").strip()


def lu_style(feature):
    return {"fillColor": LU_COLORS.get(lu_key(feature["properties"].get("land_use")), "#e2e8f0"),
            "color": "#4a5568", "weight": 0.3, "fillOpacity": 0.78}


lu_layer = folium.FeatureGroup(name="Землепользование (OSM)", show=True)
folium.GeoJson(g[["geometry", "land_use"]].to_json(), style_function=lu_style,
               tooltip=folium.GeoJsonTooltip(fields=["land_use"], aliases=["Функция"])).add_to(lu_layer)
lu_layer.add_to(m)

if len(schools):
    sch = folium.FeatureGroup(name="Школы (OSM)", show=False)
    for geom in schools.to_crs(4326).geometry:
        pt = geom.representative_point()
        folium.CircleMarker([pt.y, pt.x], radius=4, color="#1a9850", weight=1,
                            fill=True, fill_opacity=0.9, tooltip="Школа").add_to(sch)
    sch.add_to(m)

folium.LayerControl(collapsed=False).add_to(m)
map_iframe = m._repr_html_()

# ------------------------------------------------------------------ данные графиков
lu_counts = (blocks["land_use"].astype(str)
             .str.replace("LandUse.", "", regex=False)
             .replace({"None": "нет метки", "nan": "нет метки"})
             .value_counts())
sm_counts = blocks["spacematrix"].fillna("нет данных").astype(str).value_counts()
provision_bins = pd.cut(built["provision_strong"].fillna(0),
                        bins=[-0.01, 0.0001, 0.25, 0.5, 0.75, 1.0],
                        labels=["0", "0–0,25", "0,25–0,5", "0,5–0,75", "0,75–1"]).value_counts().sort_index()
fsi_hist = pd.cut(built["fsi"], bins=[0, 0.5, 1, 1.5, 2, 3, 5, 100],
                  labels=["<0,5", "0,5–1", "1–1,5", "1,5–2", "2–3", "3–5", ">5"]).value_counts().sort_index()

charts = {
    "land_use": {"labels": list(lu_counts.index), "values": [int(v) for v in lu_counts.values]},
    "spacematrix": {"labels": list(sm_counts.index), "values": [int(v) for v in sm_counts.values]},
    "provision": {"labels": [str(x) for x in provision_bins.index], "values": [int(v) for v in provision_bins.values]},
    "fsi": {"labels": [str(x) for x in fsi_hist.index], "values": [int(v) for v in fsi_hist.values]},
}

top = built.sort_values("population", ascending=False).head(10)[
    ["population", "capacity", "fsi", "gsi", "provision_strong", "area_accessibility"]
].round(2)
top_rows = "".join(
    "<tr><td>{}</td>{}</tr>".format(idx, "".join(f"<td>{v}</td>" for v in row))
    for idx, row in top.iterrows()
)

METRICS_TABLE = """
<table>
<thead><tr><th>Показатель</th><th>Что означает</th><th>Единицы</th><th>Источник</th></tr></thead>
<tbody>
<tr><td>land_use</td><td>преобладающая функция квартала</td><td>категория</td><td>OSM landuse</td></tr>
<tr><td>median_time_min</td><td>медианное время пешком до остальных кварталов</td><td>минуты</td><td>OSM walk graph</td></tr>
<tr><td>population</td><td>оценка населения квартала</td><td>чел.</td><td>оценка BlocksNet</td></tr>
<tr><td>capacity</td><td>оценка вместимости школ квартала</td><td>места</td><td>оценка BlocksNet</td></tr>
<tr><td>demand_left</td><td>непокрытый спрос на школьные места</td><td>места</td><td>расчёт</td></tr>
<tr><td>provision_strong</td><td>доля спроса, покрытая местами с учётом конкуренции</td><td>0–1</td><td>расчёт</td></tr>
<tr><td>fsi</td><td>площадь этажей / площадь квартала</td><td>коэффициент</td><td>расчёт</td></tr>
<tr><td>gsi</td><td>доля застроенной земли</td><td>0–1</td><td>расчёт</td></tr>
<tr><td>mxi</td><td>смешанность функций</td><td>коэффициент</td><td>расчёт</td></tr>
<tr><td>osr</td><td>открытые пространства на площадь этажей</td><td>коэффициент</td><td>расчёт</td></tr>
<tr><td>spacematrix</td><td>морфотип по Spacematrix</td><td>категория</td><td>расчёт</td></tr>
<tr><td>strelka</td><td>морфотип по классификации «Стрелки»</td><td>категория</td><td>расчёт</td></tr>
<tr><td>area_accessibility</td><td>доступная площадь с учётом времени пути</td><td>усл. ед.</td><td>расчёт</td></tr>
</tbody></table>
"""

conclusions = f"""
<ul>
<li><b>Плотность.</b> Медианный FSI застроенных кварталов — {fsi_median}, GSI — {gsi_median}:
кварталы Eixample застроены по периметру почти полностью, внутри — дворы.</li>
<li><b>Пешая доступность.</b> Медиана времени пешком до остальных кварталов — {walk_median} мин,
максимум {walk_max} мин: район компактен, любая точка достижима пешком.</li>
<li><b>Население.</b> Модельная оценка — {ru(population)} человек. Официально в Eixample около 265 000,
то есть модель завышает примерно на 20%: норма 30 м²/чел. и достроенная этажность.</li>
<li><b>Школы.</b> Оценка вместимости — {ru(capacity)} мест при спросе {ru(demand)} мест.
Дефицит возникает в {deficit_blocks} кварталах, средняя обеспеченность — {provision_mean}.</li>
<li><b>Землепользование.</b> OSM размечает не все кварталы, поэтому доли функций описывают
только размеченную часть выборки; для остальных функция не определена.</li>
</ul>
"""

page = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Eixample, Barcelona — кварталы и метрики</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  body {{ font-family: "Segoe UI", Roboto, Arial, sans-serif; margin: 0; background: #f7f7f9; color: #1f2933; }}
  .wrap {{ max-width: 1180px; margin: 0 auto; padding: 24px; }}
  h1 {{ font-size: 26px; margin: 0 0 4px; }}
  h3 {{ margin: 0 0 12px; font-size: 17px; }}
  .sub {{ color: #616e7c; margin-bottom: 20px; }}
  .kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 20px; }}
  .kpi {{ background: #fff; border-radius: 10px; padding: 14px 16px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
  .kpi b {{ display: block; font-size: 22px; }}
  .kpi span {{ color: #616e7c; font-size: 11px; text-transform: uppercase; letter-spacing: .04em; }}
  .card {{ background: #fff; border-radius: 10px; padding: 16px; margin-bottom: 18px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
  .grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }}
  @media (max-width: 860px) {{ .grid2 {{ grid-template-columns: 1fr; }} }}
  iframe {{ width: 100%; height: 560px; border: 0; border-radius: 8px; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
  th, td {{ border-bottom: 1px solid #e4e7eb; padding: 6px 8px; text-align: left; }}
  th {{ background: #f0f4f8; font-weight: 600; }}
  .note {{ background: #fff8e6; border-left: 4px solid #f0b429; padding: 12px 16px; border-radius: 6px; margin: 16px 0; font-size: 14px; }}
  ul {{ margin: 0; padding-left: 20px; line-height: 1.55; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>Eixample, Barcelona — кварталы и метрики</h1>
  <div class="sub">Практика 2 · BlocksNet 1.0.0a9 · {len(blocks)} кварталов · {area_ha:.0f} га ·
  данные OpenStreetMap (выгрузка Geofabrik от 19.10.2026)</div>

  <div class="kpis">
    <div class="kpi"><span>Население (оценка)</span><b>{ru(population)}</b></div>
    <div class="kpi"><span>Мест в школах (оценка)</span><b>{ru(capacity)}</b></div>
    <div class="kpi"><span>Медианный FSI</span><b>{fsi_median}</b></div>
    <div class="kpi"><span>Медианный GSI</span><b>{gsi_median}</b></div>
    <div class="kpi"><span>Пешком, медиана</span><b>{walk_median} мин</b></div>
    <div class="kpi"><span>Кварталов с дефицитом школ</span><b>{deficit_blocks}</b></div>
  </div>

  <div class="card">
    {map_iframe}
  </div>
  <div class="note">Переключайте слои в правом верхнем углу карты. Население, вместимость школ
  и часть этажности — модельные оценки BlocksNet, а не официальная статистика.</div>

  <div class="grid2">
    <div class="card"><canvas id="landuse" height="220"></canvas></div>
    <div class="card"><canvas id="provision" height="220"></canvas></div>
    <div class="card"><canvas id="fsi" height="220"></canvas></div>
    <div class="card"><canvas id="spacematrix" height="220"></canvas></div>
  </div>

  <div class="card"><h3>Что означают показатели</h3>{METRICS_TABLE}</div>
  <div class="card"><h3>Выводы</h3>{conclusions}</div>

  <div class="card">
    <h3>Топ-10 кварталов по населению</h3>
    <table>
      <thead><tr><th>Квартал</th><th>Население</th><th>Мест в школах</th><th>FSI</th><th>GSI</th>
      <th>Обеспеченность</th><th>Доступность</th></tr></thead>
      <tbody>{top_rows}</tbody>
    </table>
  </div>

  <div class="note">Ограничения: границы кварталов построены по осям улиц, а не по кадастру;
  землепользование размечено только там, где в OSM есть landuse; доступность считается только пешком,
  без общественного транспорта и рельефа.</div>
</div>
<script>
const DATA = {json.dumps(charts, ensure_ascii=False)};
const PALETTE = ['#2b6cb0','#c53030','#2f855a','#6b46c1','#d69e2e','#2c7a7b','#975a16','#4a5568'];
function draw(id, title, obj, horizontal) {{
  new Chart(document.getElementById(id), {{
    type: 'bar',
    data: {{ labels: obj.labels, datasets: [{{ data: obj.values, backgroundColor: PALETTE }}] }},
    options: {{
      indexAxis: horizontal ? 'y' : 'x',
      plugins: {{ legend: {{ display: false }}, title: {{ display: true, text: title, font: {{ size: 14 }} }} }},
      scales: {{ x: {{ beginAtZero: true }}, y: {{ beginAtZero: true }} }}
    }}
  }});
}}
draw('landuse', 'Землепользование: число кварталов', DATA.land_use, true);
draw('provision', 'Обеспеченность школами (доля покрытого спроса)', DATA.provision, false);
draw('fsi', 'Распределение FSI по застроенным кварталам', DATA.fsi, false);
draw('spacematrix', 'Морфотипы Spacematrix', DATA.spacematrix, true);
</script>
</body>
</html>
"""

with open(OUT, "w", encoding="utf-8") as fh:
    fh.write(page)

print("dashboard.html:", round(os.path.getsize(OUT) / 1e6, 2), "MB")
print("кварталов:", len(blocks), "| застроенных:", len(built), "| школ:", len(schools))
