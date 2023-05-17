from flask import Flask, render_template, url_for, redirect

app = Flask(__name__)


@app.route('/')
def index():
    return redirect(url_for('home'))


@app.route('/home')
def home():
    fig = createMapbox()
    return render_template('home.html', fig=fig)


def createMapbox():
    # Importo librerias

    import plotly.graph_objects as go
    import pandas as pd
    import json
    import numpy as np
    from scipy.interpolate import griddata

    long = []
    lati = []
    aci = []

    # Hago GET en la API, organizo al informacion obtenida en una lista
    url = "http://siata.gov.co:8089/estacionesAirePM25/cf7bb09b4d7d859a2840e22c3f3a9a8039917cc3"
    webcap = pd.read_json(url)
    webcap = webcap.datos.values.tolist()

    # Por cada dato de la lista (equivalente a la ultima lectura de un sensor)
    # adiciono el dato correspondiente a las listas de longitud, latitud y aci
    for i in webcap:
        sense = {
            "code": i['codigo'],
            "name": i['nombre'],
            "coords": {'lat': i['coordenadas'][0]['latitud'], "lon": i['coordenadas'][0]['longitud']},
            "ACI": i['valorICA'],
            "time": i['ultimaActualizacion']
        }
        senseStr = json.dumps(sense, indent=4)
        # En algunos casos los sensores lanzan un valor aci
        # de -999 (posiblemente sea su codigo de error)
        if sense['ACI'] < 0:
            continue
        long.append(sense['coords']['lon'])
        lati.append(sense['coords']['lat'])
        aci.append(pm25_to_aqi(sense['ACI']))

    # Defino mi recuadro de interpolacion
    minlon = min(long)
    maxlon = max(long)
    minlat = min(lati)
    maxlat = max(lati)

    # Creo la grilla de 100x100
    grid_x, grid_y = np.mgrid[minlon:maxlon:100j, minlat:maxlat:100j]

    # La variable points contendra los valores reales de longitud y latitud
    points = []
    for i in range(len(lati)):
        points.append([long[i], lati[i]])
    points = np.array(points)
    # print("\n================POINTS================")
    # print(points)
    # print("\n================================")

    # Genero la interpolacion con el metodo cubico

    # grid_z0 = griddata(points, aci, (grid_x, grid_y),
    #                    method='nearest', fill_value=0)
    # grid_z1 = griddata(points, aci, (grid_x, grid_y),
    #                    method='linear', fill_value=0)
    grid_z2 = griddata(points, aci, (grid_x, grid_y),
                       method='cubic', fill_value=0)

    # Los datos deben estar en un arreglo de una unica dimension,
    # por lo tanto aplico flatten y list
    grid_x = list(grid_x.flatten())
    grid_y = list(grid_y.flatten())
    # grid_z0 = list(grid_z0.flatten())
    # grid_z1 = list(grid_z1.flatten())
    grid_z2 = list(grid_z2.flatten())

    # print("\n================GRID X================")
    # print(grid_x)
    # print("\n================================")
    # print("\n================GRID Y================")
    # print(grid_y)
    # print("\n================================")
    # print("\n================GRID Z0================")
    # print(grid_z0)
    # print("\n================================")
    # print("\n================GRID Z1================")
    # print(grid_z1)
    # print("\n================================")
    # print("\n================GRID Z2================")
    # print(grid_z2)
    # print("\n================================")

    # Creamos el layout
    layout = go.Layout(
        mapbox=dict(
            center=dict(
                lat=np.mean(lati),
                lon=np.mean(long)
            ),
            style='stamen-terrain',
            zoom=9.5,
        )
    )

    # Crear la escala de colores personalizada
    colorscale = [
        [0, 'rgb(57, 160, 51)'],
        [0.2, 'rgb(212, 202, 47)'],
        [0.4, 'rgb(231, 88, 52)'],
        [0.6, 'rgb(234, 81, 159)'],
        [0.8, 'rgb(151, 90, 160)'],
        [1, 'rgb(191, 33, 51)']
    ]
    # Creamos el mapa con los datos y el layout
    data = [
        go.Densitymapbox(
            lat=grid_y,
            lon=grid_x,
            z=grid_z2,
            radius=10,
            opacity=.6,
            zmax=300,
            zmin=0,
            colorscale=colorscale
        )
    ]

    fig = go.Figure(data=data, layout=layout)

    fig.update_layout(margin={"r": 0, "t": 0, "l": 0,
                      "b": 0})

    return fig.to_html("./templates/mapbox.html",
                       include_plotlyjs="cdn",
                       full_html=False,
                       div_id="mapbox")


def pm25_to_aqi(pm25):

    ih = 0
    il = 0
    bphi = 0
    bplo = 0

    if pm25 < 0:
        raise ValueError("PM2.5 concentration cannot be negative.")
    elif pm25 > 500:
        raise ValueError(
            "PM2.5 concentration exceeds maximum limit of 500 µg/m³.")
    elif pm25 > 350.5:
        ih = 500
        il = 401
        bphi = 500
        bplo = 350.5
    elif pm25 > 250.5:
        ih = 400
        il = 301
        bphi = 350.4
        bplo = 250.5
    elif pm25 > 150.5:
        ih = 300
        il = 201
        bphi = 250.4
        bplo = 150.5
    elif pm25 > 55.5:
        ih = 200
        il = 151
        bphi = 150.4
        bplo = 55.5
    elif pm25 > 35.5:
        ih = 150
        il = 101
        bphi = 55.4
        bplo = 35.5
    elif pm25 > 12.1:
        ih = 100
        il = 51
        bphi = 35.4
        bplo = 12.1
    elif pm25 >= 0:
        ih = 50
        il = 0
        bphi = 12
        bplo = 0

    aqi = ((ih - il)/(bphi - bplo)) * (pm25 - bplo) + il

    return int(round(aqi))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
