import pandas as pd
import numpy as np
import os
import nltk
import rect_coordinate
import json
import requests
import string
from pandas.io.json import json_normalize
import re

nonalpha = string.digits + string.punctuation + string.whitespace

rootdir = "rivierkaart/geogegevens"
jsondir = "rivierkaart/kaartseries-vu/rivierkaart.json"
csvdir = "rivierkaart/csv/rivierkaart-dlcs.csv"

dlcs_query = "https://dlc.services/iiif-resource/7/string1string2string3/"

df_dlcs = pd.read_csv(csvdir)               # Import DLCS .csv file
df_json = pd.read_json(jsondir)             # Import VU .json file

df_baseset = pd.DataFrame.from_records(df_json.base_set.values)     # Convert base_set column into its own dataframe
gr_series = df_baseset.groupby(["editie", "serie"]).indices         # Group the files by editie and serie
series_keys = list(gr_series.keys())                                # Get the keys of each group

df_georef = pd.DataFrame(columns=['File', 'uuid', 'serie', 'Geo Coordinate', 'Image Coordinate', 'width', 'height'])
df_geomissing = pd.DataFrame(columns=['File', 'serie', 'uuid', 'Reason'])

for i in range(len(series_keys)):                               # Go through each group
    key = series_keys[i]                                        # Get edition and series data for group
    seq1 = gr_series[key][0]                                    # Get first image of group

    edition = df_baseset["editie"][seq1].replace(" ", "_").replace("-", "_").lower()  # Get edition number
    series = df_baseset["serie"][seq1].replace(" ", "_").lower()                      # Get series number

    if edition and series:  # Check if edition or series exists
        newdir = rootdir + "/" + edition + "/Serie_" + series                         # Make base directory

        title = df_json.display_title[seq1]                                           # Get title of first image
        files = [f for f in os.listdir(newdir)
                 if os.path.isfile(os.path.join(newdir, f))]  # List all files in directory
        edit_distance = []

        # Compare file names in folder to first file name from .json file
        for k in files:
            edit_distance = np.append(edit_distance,
                                      nltk.edit_distance(title, k,
                                                         substitution_cost=1, transpositions=False))
        # Get file name with the closest resemblance (edit distance)
        filename = files[np.argmin(edit_distance)]  # Get file name

        csv_index = df_dlcs.loc[df_dlcs["Origin"].str.contains(filename, case=False)]  # Get dlcs .csv data

        ref1 = str(csv_index.Reference1.values[0])
        ref2 = str(csv_index.Reference2.values[0])
        ref3 = str(csv_index.Reference3.values[0])

        json_url = dlcs_query+ref1+"/"+ref2+"/"+ref3            # construct json url

        seq_json = requests.get(json_url).json()  # Get .json file

        # Add data to metadata
        meta = [
            {
                "label": "Title",
                "value": df_baseset.titel[seq1]
            },
            {
                "label": "Editie",
                "value": df_baseset.editie[seq1]
            },
            {
                "label": "Serie",
                "value": df_baseset.serie[seq1]
            },
            {
                "label": "Geoplaza Kaartseries",
                "value": "<a href=\"https://geoplaza.vu.nl/mapseries/search?&fs[base_series]="
                         "Rivierkaarten&fs[base_set]=rvr^{},%20serie%20{}\">{}</a>".format(df_baseset.editie[seq1],
                                                                                           df_baseset.serie[seq1],
                                                                                           df_baseset.display_title[seq1])
            }
        ]

        seq_json["metadata"] = meta     # Add meta data to .json

        for j in range(len(seq_json['sequences'][0]['canvases'])):  # Go through all photo's in sequence
            service_id = seq_json['sequences'][0]['canvases'][j]['images'][0]['resource']['service']['@id']
            uuid = service_id.split('/')[-1]        # Get UUID of image
            csv_index = df_dlcs.loc[df_dlcs["ID"].str.contains(uuid, case=False)]  # Get dlcs .csv data
            csv_filename = csv_index['Origin'].values[0].split('/')[-1]\
                .strip('.jpg').replace('-', ' ')        # Get filename

            edit_distance = []
            ## Compare file names in folder to file name from .json file
            for k in range(len(gr_series[key])):
                rep_key = gr_series[key][k]
                fnd_url = df_json['copies'][rep_key]
                for l in range(len(fnd_url)):
                    # rep_url = pd.DataFrame.from_records(fnd_url[l])
                    if 'electronic_versions' in fnd_url[l]:
                        fnd_rep = fnd_url[l]['electronic_versions']
                        if fnd_rep:
                            if 'repository_url' in fnd_rep[0]:
                                rep_url = fnd_rep[0]['repository_url']
                                json_file = rep_url.split('/')[-1]
                                break
                            else:
                                json_file = df_json.display_title[gr_series[key]][rep_key]
                        else:
                            json_file = df_json.display_title[gr_series[key]][rep_key]
                    else:
                        json_file = df_json.display_title[gr_series[key]][rep_key]

                edit_distance = np.append(edit_distance,
                                          nltk.edit_distance(csv_filename, json_file,
                                                             substitution_cost=1, transpositions=False))

            json_index = np.argmin(edit_distance)  # Get file name
            title_instance = df_json['titel'][gr_series[key][json_index]]       # Get title name from .json file
            seq_json['sequences'][0]['canvases'][j]['label'] = title_instance
            geo = df_json.base_sheet[gr_series[key][json_index]]['region']['geom4326']
            if geo:
                geo = geo.strip('POLYGON ((').strip('))')
                geo = np.asarray(re.split(', | ', geo.strip('POLYGON ((').strip('))')))
                geo = geo.astype(np.float_).reshape((5, 2))
                # geo = geo.reshape((5, 2))
                file = csv_index['Origin'].values[0].split('/')[-1]
                fileloc = rootdir + "/" + edition + "/Serie_" + series + "/" + file
                [im_coord, img_size] = rect_coordinate.get_coordinate(fileloc)

                if (im_coord > 0).all():

                    sortx = np.argsort(im_coord[:, 0])
                    sorty = np.argsort(im_coord[:, 1])

                    try:
                        im_coord_cc = im_coord[np.array([
                            [f for f in sortx[0:2] if (sorty[2:4] == f).any()],
                            [f for f in sortx[2:4] if (sorty[2:4] == f).any()],
                            [f for f in sortx[2:4] if (sorty[0:2] == f).any()],
                            [f for f in sortx[0:2] if (sorty[0:2] == f).any()]])
                        ]
                    except:
                        df_geomissing = df_geomissing.append({'File': csv_filename,
                                                              'uuid': uuid,
                                                              'Reason': 'Cannot reorder'
                                                              }, ignore_index=True)

                    df_georef = df_georef.append({'File': csv_filename,
                                                  'uuid': uuid,
                                                  'serie': key,
                                                  'Geo Coordinate': geo,
                                                  'Image Coordinate': im_coord_cc,
                                                  'width': img_size[0],
                                                  'height': img_size[1]}, ignore_index=True)

                else:
                    print('Negative number in coordinates')

                    df_geomissing = df_geomissing.append({'File': title_instance,
                                                          'serie': key,
                                                          'uuid': uuid,
                                                          'Reason': 'Negative number in coordinates'
                                                          }, ignore_index=True)

            else:
                print("Missing geo data for {}".format(title_instance))
                df_geomissing = df_geomissing.append({'File': title_instance,
                                                      'uuid': uuid,
                                                      'Reason': 'Missing geo data'
                                                      }, ignore_index=True)


        # Serializing json
        # json_object = json.dumps(seq_json, indent=10)
        #
        # json_filename = ref1+'_'+df_baseset.display_title[seq1].replace(" ", "_").replace(",", "").lower()
        # # Writing to sample.json
        # with open("{}.json".format(json_filename), "w") as outfile:
        #     outfile.write(json_object)

df_georef.to_csv('georef.csv', index=False)
df_geomissing.to_csv('geo_missing.csv', index=False)
