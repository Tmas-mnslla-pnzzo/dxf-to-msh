import ezdxf
import csv
import numpy as np
import triangle
import matplotlib.pyplot as plt
from math import cos, sin, pi
from config import *
import sys


def eliminar_puntos_duplicados(puntos, segmentos, clasificaciones):
    puntos_unicos, indices_unicos = np.unique(puntos, axis=0, return_inverse=True)
    
    # Filtrar segmentos para evitar índices fuera de rango
    segmentos_actualizados = [
        [indices_unicos[s[0]], indices_unicos[s[1]]]
        for s in segmentos if s[0] < len(indices_unicos) and s[1] < len(indices_unicos)
    ]

    clasificaciones_actualizadas = [0] * len(puntos_unicos)
    for i, idx in enumerate(indices_unicos):
        if idx < len(clasificaciones_actualizadas):  # Evitar fuera de rango
            clasificaciones_actualizadas[idx] = clasificaciones[i]

    return puntos_unicos, segmentos_actualizados, clasificaciones_actualizadas


def leer_entidades_dxf_por_capa(ruta_dxf, prefijo_capa_agujeros, num_puntos_intermedios_linea, num_puntos_intermedios_circulo, num_puntos_intermedios_spline, indice_punto_contorno, indice_punto_agujero, densidad_puntos):
    print(f"Leyendo archivo DXF: {ruta_dxf}")
    doc = ezdxf.readfile(ruta_dxf)
    msp = doc.modelspace()

    puntos_contorno = []
    segmentos_contorno = []
    conj_puntos_agujeros = []
    conj_segmentos_agujeros = []
    clasificaciones_contorno = []
    clasificaciones_agujeros = []

    capas_agujeros = set()

    print(f"Buscando capas con prefijo: {prefijo_capa_agujeros}")
    for entity in msp:
        if entity.dxf.layer.startswith(prefijo_capa_agujeros):
            capas_agujeros.add(entity.dxf.layer)

    print(f"Procesando entidades del contorno...")
    for entity in msp:
        if entity.dxftype() in ['SPLINE', 'LINE', 'CIRCLE']:
            if not entity.dxf.layer.startswith(prefijo_capa_agujeros):
                if entity.dxftype() == 'SPLINE':
                    puntos_entity = np.array([[p.x, p.y] for p in entity.flattening(distance=num_puntos_intermedios_spline)])
                elif entity.dxftype() == 'LINE':
                    start = np.array([round(entity.dxf.start.x, presicion), round(entity.dxf.start.y, presicion)])
                    end = np.array([round(entity.dxf.end.x, presicion), round(entity.dxf.end.y, presicion)])
                    longitud = np.linalg.norm(end - start)
                    num_puntos_adaptativo = max(int(longitud * densidad_puntos), num_puntos_intermedios_linea)  # Ajusta el divisor 0.5 según necesites     
                    puntos_entity = np.array([start + (end - start) * t / num_puntos_adaptativo for t in range(num_puntos_adaptativo + 1)])
                elif entity.dxftype() == 'CIRCLE':
                    centro = np.array([entity.dxf.center.x, entity.dxf.center.y])
                    radio = entity.dxf.radius
                    angulos = np.linspace(0, 2 * pi, num_puntos_intermedios_circulo, endpoint=False)
                    puntos_entity = np.array([centro + radio * np.array([cos(a), sin(a)]) for a in angulos])
                    puntos_entity = np.vstack([puntos_entity, puntos_entity[0]])

                num_puntos = len(puntos_entity)
                segmentos_entity = [[indice_punto_contorno + i, indice_punto_contorno + i + 1] for i in range(num_puntos - 1)]

                puntos_contorno.extend(puntos_entity)
                segmentos_contorno.extend(segmentos_entity)
                if entity.dxf.layer == "0":
                    clasificaciones_contorno.extend([1] * num_puntos)
                else:
                    clasificaciones_contorno.extend([int(entity.dxf.layer[3:])+1] * num_puntos)
                indice_punto_contorno += num_puntos

    print(f"Procesando agujeros...")
    for capa_agujero in capas_agujeros:
        puntos_agujero = []
        segmentos_agujero = []
        clasificaciones_agujero = []

        for entity in msp:
            if entity.dxftype() in ['SPLINE', 'LINE', 'CIRCLE'] and entity.dxf.layer == capa_agujero:
                if entity.dxftype() == 'SPLINE':
                    puntos_entity = np.array([[p.x, p.y] for p in entity.flattening(distance=num_puntos_intermedios_spline)])
                elif entity.dxftype() == 'LINE':
                    start = np.array([round(entity.dxf.start.x, presicion), round(entity.dxf.start.y, presicion)])
                    end = np.array([round(entity.dxf.end.x, presicion), round(entity.dxf.end.y, presicion)])
                    longitud = np.linalg.norm(end - start)
                    num_puntos_adaptativo = max(int(longitud * densidad_puntos), num_puntos_intermedios_linea)  # Ajusta el divisor 0.5 según necesites     
                    puntos_entity = np.array([start + (end - start) * t / num_puntos_adaptativo for t in range(num_puntos_adaptativo + 1)])
                elif entity.dxftype() == 'CIRCLE':
                    centro = np.array([entity.dxf.center.x, entity.dxf.center.y])
                    radio = entity.dxf.radius
                    angulos = np.linspace(0, 2 * pi, num_puntos_intermedios_circulo, endpoint=False)
                    puntos_entity = np.array([centro + radio * np.array([cos(a), sin(a)]) for a in angulos])
                    puntos_entity = np.vstack([puntos_entity, puntos_entity[0]])

                num_puntos = len(puntos_entity)
                segmentos_entity = [[i, i + 1] for i in range(num_puntos - 1)]  # Segmentos internos                
                clasific_entity=[-int(entity.dxf.layer[3:])-1] * num_puntos
               
                puntos_entity, segmentos_entity, clasific_entity = eliminar_puntos_duplicados(puntos_entity, segmentos_entity, clasific_entity)
             
                puntos_agujero.extend(puntos_entity)
                segmentos_agujero.extend(segmentos_entity)
                clasificaciones_agujero.extend([-int(entity.dxf.layer[3:])-1] * num_puntos)
                indice_punto_agujero += num_puntos

        if puntos_agujero:
            conj_puntos_agujeros.append(np.array(puntos_agujero)[:, :2])
            conj_segmentos_agujeros.append(segmentos_agujero)
            clasificaciones_agujeros.append(clasificaciones_agujero)
    
    puntos_contorno, segmentos_contorno, clasificaciones_contorno = eliminar_puntos_duplicados(np.array(puntos_contorno), segmentos_contorno, clasificaciones_contorno)
    
    print(f"Lectura del DXF completada.")
    return (
        np.array(puntos_contorno)[:, :2], segmentos_contorno, conj_puntos_agujeros, conj_segmentos_agujeros,
        clasificaciones_contorno, clasificaciones_agujeros
    )

def generar_malla_triangle(puntos_contorno, segmentos_contorno, conj_puntos_agujeros, 
                            conj_segmentos_agujeros, max_area, clasificaciones_contorno, clasificaciones_agujeros):
    print(f"Generando malla con Triangle...")
    puntos_combinados = np.copy(puntos_contorno)
    segmentos_combinados = list(segmentos_contorno)
    agujeros = []
    clasificaciones = list(clasificaciones_contorno)

    esquinas = {tuple(p) for p in puntos_contorno}
    indice_offset = len(puntos_contorno)
    
    for puntos_agujero, segmentos_agujero, clasificaciones_agujero in zip(conj_puntos_agujeros, conj_segmentos_agujeros, clasificaciones_agujeros):
        puntos_combinados = np.vstack([puntos_combinados, puntos_agujero])
        segmentos_combinados.extend([[indice_offset + i, indice_offset + j] for i, j in segmentos_agujero])
        
        centro_agujero = np.mean(puntos_agujero, axis=0)
        agujeros.append(centro_agujero)
        
        clasificaciones.extend(clasificaciones_agujero)
        indice_offset += len(puntos_agujero)

    datos = {
        "vertices": puntos_combinados,
        "segments": segmentos_combinados,
    }

    if agujeros:
        datos["holes"] = agujeros
        
    malla = triangle.triangulate(datos, f"pqa{max_area}")

    vertices_generados = {tuple(p) for p in malla["vertices"]}
    esquinas_perdidas = esquinas - vertices_generados
    if esquinas_perdidas:
        print(f"Advertencia: {len(esquinas_perdidas)} nodos de esquina no se incluyeron en la malla.")
        print(esquinas_perdidas)

    clasificaciones_finales = []
    for punto in malla["vertices"]:
        coincidencia = False
        for i, punto_original in enumerate(puntos_combinados):
            if np.allclose(punto, punto_original):
                clasificaciones_finales.append(clasificaciones[i])
                coincidencia = True
                break
        if not coincidencia:
            clasificaciones_finales.append(0)

    malla["clasificaciones"] = clasificaciones_finales
    print(f"Malla generada exitosamente.")
    
    return malla

def guardar_malla_vtk(nombre_archivo, malla):
    print(f"Guardando malla en formato VTK: {nombre_archivo}.vtk")
    try:
        with open(nombre_archivo, "w") as archivo:
            archivo.write("# vtk DataFile Version 3.0\n")
            archivo.write("Malla generada con Triangle\n")
            archivo.write("ASCII\n")
            archivo.write("DATASET UNSTRUCTURED_GRID\n")
    
            archivo.write(f"POINTS {len(malla['vertices'])} float\n")
            for punto in malla["vertices"]:
                archivo.write(f"{punto[0]} {punto[1]} 0.0\n")
        
            num_triangulos = len(malla["triangles"])
            archivo.write(f"CELLS {num_triangulos} {4 * num_triangulos}\n")
            for triangulo in malla["triangles"]:
                archivo.write(f"3 {triangulo[0]} {triangulo[1]} {triangulo[2]}\n")
        
            archivo.write(f"CELL_TYPES {num_triangulos}\n")
            archivo.write(" ".join(["5"] * num_triangulos))
            archivo.write("\n")
            print("Malla generada y guardada en " + nombre_archivo + ".vtk")
    except KeyError as e:
        print(f"Error: Falta una clave en el diccionario 'malla'. Detalle: {e}")
    except IOError as e:
        print(f"Error de entrada/salida al guardar el archivo. Detalle: {e}")
    except TypeError as e:
        print(f"Error: Los datos en 'malla' no tienen el formato esperado. Detalle: {e}")
    except Exception as e:
        print(f"No se pudo guardar la malla en formato vtk. Error inesperado: {e}")

def guardar_malla_npz(nombre_archivo, malla): 
    print(f"Guardando malla en formato NPZ: {nombre_archivo}.npz")
    try:
        np.savez(
            nombre_archivo,
            vertices=malla["vertices"],
            triangles=malla["triangles"],
            clasificaciones=malla["clasificaciones"]
        )
        print("Malla generada y guardada en " + nombre_archivo + ".npz")
    except KeyError as e:
        print(f"Error: Falta una clave en el diccionario 'malla'. Detalle: {e}")
    except Exception as e:
        print(f"No se pudo guardar la malla en formato npz. Error: {e}")

import csv

def guardar_malla_csv(nombre_archivo, malla):
    nombre_archivo_t = nombre_archivo + "_elementos.csv"  
    nombre_archivo_p = nombre_archivo + "_puntos.csv" 
    nombre_archivo_c = nombre_archivo + "_clas.csv"  
    print(f"Guardando malla en formato CSV: {nombre_archivo}")
    
    try:
        with open(nombre_archivo_p, "w", newline='') as archivo:
            writer = csv.writer(archivo)

            for punto in malla["vertices"]:
                writer.writerow([float(punto[0]), float(punto[1])])
        archivo.close()
        print(f"Malla guardada en {nombre_archivo_p}")
        
        with open(nombre_archivo_t, "w", newline='') as archivo:
            writer = csv.writer(archivo)
            
            for triangulo in malla["triangles"]:
                writer.writerow([int(triangulo[0]), int(triangulo[1]), int(triangulo[2])])
        archivo.close()
        print(f"Malla guardada en {nombre_archivo_t}")
    
        with open(nombre_archivo_c, "w", newline='') as archivo:
            writer = csv.writer(archivo)
            
            for clas in malla["clasificaciones"]:
                if clas==None:
                    writer.writerow(["None"])
                else:
                    writer.writerow([clas])
        archivo.close()
        print(f"Malla guardada en {nombre_archivo_c}")

    except KeyError as e:
        print(f"Error: Falta una clave en el diccionario 'malla'. Detalle: {e}")
    except IOError as e:
        print(f"Error de entrada/salida al guardar el archivo. Detalle: {e}")
    except TypeError as e:
        print(f"Error: Los datos en 'malla' no tienen el formato esperado. Detalle: {e}")
    except Exception as e:
        print(f"No se pudo guardar la malla en formato CSV. Error inesperado: {e}")

def visualizar_malla(malla):
    print("Visualizando malla...")
    vertices_xy = np.array([vertice[:2] for vertice in malla["vertices"]])
    plt.triplot(
        vertices_xy[:, 0],
        vertices_xy[:, 1],
        malla["triangles"]
    )
    plt.gca().set_aspect("equal")
    plt.title("Malla generada con Triangle")
    plt.show()
