import ezdxf
import numpy as np
import triangle
import matplotlib.pyplot as plt
from math import cos, sin, pi

def leer_entidades_dxf_por_capa(ruta_dxf, prefijo_capa_agujeros):
    doc = ezdxf.readfile(ruta_dxf)
    msp = doc.modelspace()

    puntos_contorno = []
    segmentos_contorno = []
    conj_puntos_agujeros = []
    conj_segmentos_agujeros = []
    clasificaciones_contorno = []
    clasificaciones_agujeros = []
    capas_agujeros = set()

    presicion=6
    num_puntos_intermedios_linea = 10
    num_puntos_intermedios_circulo = 10
    num_puntos_intermedios_spline = 0.1
    indice_punto_contorno = 0

    for entity in msp:
        if entity.dxf.layer.startswith(prefijo_capa_agujeros):
            capas_agujeros.add(entity.dxf.layer)

    for entity in msp:
        if entity.dxftype() in ['SPLINE', 'LINE', 'CIRCLE']:
            if not entity.dxf.layer.startswith(prefijo_capa_agujeros):
                if entity.dxftype() == 'SPLINE':
                    puntos_entity = np.array([[p.x, p.y] for p in entity.flattening(distance=num_puntos_intermedios_spline)])
                elif entity.dxftype() == 'LINE':
                    start = np.array([round(entity.dxf.start.x,presicion), round(entity.dxf.start.y,presicion)])
                    end = np.array([round(entity.dxf.end.x,presicion), round(entity.dxf.end.y,presicion)])
                    puntos_entity = np.array([start + (end - start) * t / num_puntos_intermedios_linea for t in range(num_puntos_intermedios_linea + 1)])
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
                    clasificaciones_contorno.extend(["ext0"] * num_puntos)  
                else:
                    clasificaciones_contorno.extend([entity.dxf.layer] * num_puntos)  
                indice_punto_contorno += num_puntos

    for capa_agujero in capas_agujeros:
        puntos_agujero = []
        segmentos_agujero = []
        clasificaciones_agujero = []
        indice_punto_agujero = 0

        for entity in msp:
            if entity.dxftype() in ['SPLINE', 'LINE', 'CIRCLE'] and entity.dxf.layer == capa_agujero:
                if entity.dxftype() == 'SPLINE':
                    puntos_entity = np.array([[p.x, p.y] for p in entity.flattening(distance=num_puntos_intermedios_spline)])
                elif entity.dxftype() == 'LINE':
                    start = np.array([round(entity.dxf.start.x,presicion), round(entity.dxf.start.y,presicion)])
                    end = np.array([round(entity.dxf.end.x,presicion), round(entity.dxf.end.y,presicion)])
                    puntos_entity = np.array([start + (end - start) * t / num_puntos_intermedios_linea for t in range(num_puntos_intermedios_linea + 1)])
                elif entity.dxftype() == 'CIRCLE':
                    centro = np.array([entity.dxf.center.x, entity.dxf.center.y])
                    radio = entity.dxf.radius
                    angulos = np.linspace(0, 2 * pi, num_puntos_intermedios_circulo, endpoint=False)
                    puntos_entity = np.array([centro + radio * np.array([cos(a), sin(a)]) for a in angulos])
                    puntos_entity = np.vstack([puntos_entity, puntos_entity[0]]) 

                num_puntos = len(puntos_entity)
                segmentos_entity = [[indice_punto_agujero + i, indice_punto_agujero + j] for i, j in zip(range(num_puntos - 1), range(1, num_puntos))]

                puntos_agujero.extend(puntos_entity)
                segmentos_agujero.extend(segmentos_entity)
                clasificaciones_agujero.extend([capa_agujero] * num_puntos) 
                indice_punto_agujero += num_puntos

        if puntos_agujero:
            conj_puntos_agujeros.append(np.array(puntos_agujero)[:, :2])
            conj_segmentos_agujeros.append(segmentos_agujero)
            clasificaciones_agujeros.append(clasificaciones_agujero)
    
    return (
        np.array(puntos_contorno)[:, :2], segmentos_contorno, conj_puntos_agujeros, conj_segmentos_agujeros,
        clasificaciones_contorno, clasificaciones_agujeros
    )

def generar_malla_triangle(puntos_contorno, segmentos_contorno, conj_puntos_agujeros, conj_segmentos_agujeros, max_area, clasificaciones_contorno, clasificaciones_agujeros):
    puntos_combinados = np.copy(puntos_contorno)
    segmentos_combinados = list(segmentos_contorno)
    agujeros = []
    clasificaciones = list(clasificaciones_contorno)  

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

    # Solo agregamos "holes" si hay agujeros
    if agujeros:
        datos["holes"] = agujeros

    # Generar la malla con Triangle
    malla = triangle.triangulate(datos, f"pqa{max_area}")

    # Asignar clasificaciones a los puntos de la malla
    clasificaciones_finales = []
    for punto in malla["vertices"]:
        # Buscar si el punto coincide con alguno de los puntos originales
        coincidencia = False
        for i, punto_original in enumerate(puntos_combinados):
            if np.allclose(punto, punto_original):
                clasificaciones_finales.append(clasificaciones[i])
                coincidencia = True
                break
        if not coincidencia:
            clasificaciones_finales.append(None)  # Asignar None a los nuevos puntos

    # Agregar clasificaciones a la malla
    malla["clasificaciones"] = clasificaciones_finales

    return malla

def guardar_malla_vtk(nombre_archivo, malla):
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

def visualizar_malla(malla):
    vertices_xy = np.array([vertice[:2] for vertice in malla["vertices"]])
    plt.triplot(
        vertices_xy[:, 0],
        vertices_xy[:, 1],
        malla["triangles"]
    )
    plt.gca().set_aspect("equal")
    plt.title("Malla generada con Triangle")
    plt.show()

ruta_dxf = "t.dxf"
name = ruta_dxf[:-4]  
prefijo_capa_agujeros = "int" 
max_area = 0.1  

puntos_contorno, segmentos_contorno, conj_puntos_agujeros, conj_segmentos_agujeros, clasificaciones_contorno, clasificaciones_agujeros = leer_entidades_dxf_por_capa(
    ruta_dxf, prefijo_capa_agujeros
)

malla = generar_malla_triangle(
    puntos_contorno, segmentos_contorno, conj_puntos_agujeros, conj_segmentos_agujeros, max_area, clasificaciones_contorno, clasificaciones_agujeros
)

guardar_malla_vtk(name, malla)
guardar_malla_npz(name, malla)
visualizar_malla(malla)