import pandas as pd
import json
import numpy as np
import re
import hashlib

df_geo = pd.read_csv('georef.csv')

geo_group = df_geo.groupby(['serie']).indices
geo_keys = list(geo_group.keys())


for i in range(len(geo_keys)):
    # Opening JSON base file
    with open('base_georef.json') as json_file:
        json_base = json.load(json_file)

    json_geo = json_base
    for j in geo_group[geo_keys[i]]:
        geo_coord = df_geo.iloc[j]['Geo Coordinate'].split('\n')
        img_size = [df_geo.iloc[j]['width'], df_geo.iloc[j]['height']]
        pixel_coord = df_geo.iloc[j]['Image Coordinate'].split('\n\n')
        uuid = df_geo.iloc[j]['uuid']

        json_items = {"id": uuid,
                  "type": "Annotation",
                  "@context": [
                    "http://www.w3.org/ns/anno.jsonld",
                    "http://geojson.org/geojson-ld/geojson-context.jsonld",
                    "http://iiif.io/api/presentation/3/context.json"
                  ],
                  "motivation": "georeferencing",
                  "target": {
                    "type": "Image",
                    "source": "",
                    "service": [
                      {
                        "@id": "",
                        "type": "ImageService2"
                      }
                    ],
                    "selector": {
                      "type": "SvgSelector",
                      "value": ""
                    }
                  },
                  "body": {
                    "type": "FeatureCollection",
                    "purpose": "gcp-georeferencing",
                    "transformation": {
                      "type": "polynomial",
                      "order": 0
                    },
                    "features": [
                    ]
                  }
                }

        json_geo['items'].append(json_items)


        geo_mask = ""
        pos_json = len(json_geo['items'])-1
        for k in range(len(pixel_coord)):
            geo = np.asarray(re.findall(r"[-+]?(?:\d*\.\d+|\d+)", geo_coord[k])).astype(np.float_)
            pixel = np.asarray(re.findall(r"[-+]?(?:\d*\.\d+|\d+)", pixel_coord[k])).astype(np.float_)

            new_coord = {
                    "type": "Feature",
                        "properties": {
                          "pixelCoords": [
                            int(pixel[0]),
                            int(pixel[1])
                          ]
                        },
                        "geometry": {
                          "type": "Point",
                          "coordinates": [
                            geo[0],
                            geo[1]
                          ]
                        }
            }
            geo_mask = geo_mask + str(int(pixel[0])) + ',' + str(int(pixel[1])) + ' '

            json_geo['items'][pos_json]['body']['features'].append(new_coord)

        json_geo['items'][pos_json]['target']['source'] = 'https://dlc.services/iiif-img/7/32/'+uuid+'/full/full/0/default.jpg'
        json_geo['items'][pos_json]['target']['service'][0]['@id'] = 'https://dlc.services/iiif-img/7/32/'+uuid

        json_geo['items'][pos_json]['target']['selector']['value'] =\
            '<svg width="' + str(img_size[0]) + '" height="' + str(img_size[1]) + \
            '"><polygon points="' + geo_mask[0:-1] + '" /></svg>'

    batch_name = re.sub(r'\W+', '', geo_keys[i].replace(' ', '_'))
    with open('georef/georef_'+batch_name+'.json', 'w') as outfile:
        json.dump(json_geo, outfile)
