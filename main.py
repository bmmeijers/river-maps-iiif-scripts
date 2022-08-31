import pandas as pd
import numpy as np
import os
import nltk
import rect_coordinate
import json
import requests
import string
from pandas.io.json import json_normalize

nonalpha = string.digits + string.punctuation + string.whitespace

rootdir = "Source_data/rivierkaart/geogegevens"
jsondir = "Source_data/rivierkaart/kaartseries-vu/rivierkaart.json"
csvdir = "Source_data/rivierkaart/csv/rivierkaart-dlcs.csv"

dlcs_query = "https://dlc.services/iiif-resource/7/string1string2string3/"

df_dlcs = pd.read_csv(csvdir)               # Import DLCS .csv file
df_json = pd.read_json(jsondir)             # Import VU .json file

df_baseset = pd.DataFrame.from_records(df_json.base_set.values)     # Convert base_set column into its own dataframe
gr_series = df_baseset.groupby(["editie", "serie"]).indices         # Group the files by editie and serie
series_keys = list(gr_series.keys())                                # Get the keys of each group

filename_arr = []

for n in range(len(df_json)):
    # rep_url = pd.DataFrame.from_records(fnd_url[l])
    elec_copies = df_json.iloc[n]['copies']
    for m in range(len(elec_copies)):
        elec_vers = elec_copies[m]
        if 'electronic_versions' in elec_vers:
            fnd_rep = elec_vers['electronic_versions']
            if fnd_rep:
                if 'repository_url' in fnd_rep[0]:
                    rep_url = fnd_rep[0]['repository_url']
                    filename_arr = np.append(filename_arr, rep_url.split('/')[-1])
                    break
                else:
                    filename_arr = np.append(filename_arr,  df_json.iloc[n].display_title)
            # else:
            #     filename_arr = np.append(filename_arr,  df_json.iloc[n].display_title)
        # else:
        #     filename_arr = np.append(filename_arr,  df_json.iloc[n].display_title)

for i in range(len(series_keys)):                               # Go through each group
    key = series_keys[i]
    seq1 = gr_series[key][0]

    edition = df_baseset["editie"][seq1].replace(" ", "_").replace("-", "_").lower()  # Get edition number
    series = df_baseset["serie"][seq1].replace(" ", "_").lower()

    if edition and series:  # Check if edition or series exists
        newdir = rootdir + "/" + edition + "/Serie_" + series

        title = df_json.display_title[seq1]
        files = [f for f in os.listdir(newdir)
                 if os.path.isfile(os.path.join(newdir, f))]  # List all files in directory
        edit_distance = []

        ## Compare file names in folder to file name from .json file
        for k in files:
            edit_distance = np.append(edit_distance,
                                      nltk.edit_distance(title, k,
                                                         substitution_cost=1, transpositions=False))
        # Get file name with closest resemblance (edit distance)
        filename = files[np.argmin(edit_distance)]  # Get file name

        csv_index = df_dlcs.loc[df_dlcs["Origin"].str.contains(filename, case=False)]  # Get dlcs .csv data

        ref1 = str(csv_index.Reference1.values[0])
        ref2 = str(csv_index.Reference2.values[0])
        ref3 = str(csv_index.Reference3.values[0])

        json_url = dlcs_query+ref1+"/"+ref2+"/"+ref3

        seq_json = requests.get(json_url).json()  # Get .json file

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

        seq_json["metadata"] = meta

        for j in range(len(seq_json['sequences'][0]['canvases'])):
            service_id = seq_json['sequences'][0]['canvases'][j]['images'][0]['resource']['service']['@id']
            uuid = service_id.split('/')[-1]
            csv_index = df_dlcs.loc[df_dlcs["ID"].str.contains(uuid, case=False)]  # Get dlcs .csv data
            csv_filename = csv_index['Origin'].values[0].split('/')[-1]\
                .strip('.jpg').replace('-', ' ')                            # Get filename from .csv file

            # displ_titles = df_json.display_title[gr_series[key]].values
            # displ_titles = df_json.display_title.values

            edit_distance = []
            ## Compare file names in folder to file name from .json file
            # for k in range(len(gr_series[key])):
            #     rep_key = gr_series[key][k]
            #     fnd_url = df_json['copies'][rep_key]
            #     for m in range(len(fnd_url)):
            #         # rep_url = pd.DataFrame.from_records(fnd_url[l])
            #         if 'electronic_versions' in fnd_url[m]:
            #             fnd_rep = fnd_url[m]['electronic_versions']
            #             if fnd_rep:
            #                 if 'repository_url' in fnd_rep[0]:
            #                     rep_url = fnd_rep[0]['repository_url']
            #                     json_file = rep_url.split('/')[-1]
            #                     break
            #                 else:
            #                     json_file = df_json.display_title[gr_series[key]][rep_key]
            #             else:
            #                 json_file = df_json.display_title[gr_series[key]][rep_key]
            #         else:
            #             json_file = df_json.display_title[gr_series[key]][rep_key]
            for json_file in filename_arr:
                # if rep_url:
                #     rep_url = rep_url[0]['repository_url']
                #     json_file = rep_url.split('/')[-1]
                # else:
                #     json_file = df_json.display_title[gr_series[key]][k]
                edit_distance = np.append(edit_distance,
                                          nltk.edit_distance(csv_filename, json_file,
                                                             substitution_cost=1, transpositions=False))
            # min_edit = np.min(edit_distance)
            # if min_edit/len(csv_filename) < 0.4:
            # json_index = df_json.display_title[gr_series[key]].index[np.argmin(edit_distance)]  # Get file name
            json_index = np.argmin(edit_distance)
            # title_instance = df_json['titel'][json_index]
            title_instance = df_json['display_title'][json_index]
            seq_json['sequences'][0]['canvases'][j]['label'] = title_instance
            # geo = df_json.base_sheet[json_index]['region']['geom4326']
            # if geo:
            #     file = csv_index['Origin'].values[0].split('/')[-1]
            #     fileloc = rootdir + "/" + edition + "/Serie_" + series + "/" + file
            #     im_coord = rect_coordinate.get_coordinate(fileloc)
            #
            #     sortx = np.argsort(im_coord[:, 0])
            #     sorty = np.argsort(im_coord[:, 1])
            #
            #     im_coord_cc = im_coord[np.array([
            #         [f for f in sortx[0:2] if (sorty[2:4] == f).any()],
            #         [f for f in sortx[2:4] if (sorty[2:4] == f).any()],
            #         [f for f in sortx[2:4] if (sorty[0:2] == f).any()],
            #         [f for f in sortx[1:2] if (sorty[0:2] == f).any()]])
            #     ]
            #     #
            #     # geo = geo[10:-2].split(',')
            #     # geo_coord = []
            #     # for g in geo:
            #     #     gsplit = list(filter(None, g.split(' ')))
            #     #     geo_coord = np.append(geo_coord, np.array(gsplit).astype(float))
            #     # geo_coord = geo_coord.reshape((5, 2))
            #
            # else:
            #     print("Missing geo data for {}".format(title_instance))

        # Serializing json
        json_object = json.dumps(seq_json, indent=10)

        json_filename = ref1+'_'+df_baseset.display_title[seq1].replace(" ", "_").replace(",", "").lower()
        # Writing to sample.json
        with open("Output/JSON_manifests/{}.json".format(json_filename), "w") as outfile:
            outfile.write(json_object)



    # group_index = gr_series[key]
    # for j in range(len(group_index)):                               # Go through all photos within each group
    #     js_i = group_index[j]
    #     edition = df_baseset["editie"][js_i].replace(" ", "_").replace("-", "_").lower()  # Get edition number
    #     series = df_baseset["serie"][js_i].replace(" ", "_").lower()                      # Get series number
    #
    #     if edition and series:  # Check if edition or series exists
    #         newdir = rootdir + "/" + edition + "/Serie_" + series
    #
    #         title = df_json.display_title[js_i]
    #         files = [f for f in os.listdir(newdir)
    #                  if os.path.isfile(os.path.join(newdir, f))]  # List all files in directory
    #         edit_distance = []
    #
    #         ## Compare file names in folder to file name from .json file
    #         for k in files:
    #             edit_distance = np.append(edit_distance,
    #                                       nltk.edit_distance(title, k,
    #                                                          substitution_cost=1, transpositions=False))
    #         # Get file name with closest resemblance (edit distance)
    #         filename = files[np.argmin(edit_distance)]  # Get file name
    #
    #         csv_index = df_dlcs.loc[df_dlcs["Origin"].str.contains(filename, case=False)]  # Get dlcs .csv data
    #
    #
    #     ## TO DO:
    #         # Get json of first file in sequence and use it as base file
    #         # Put meta data in base file
    #         # Add series label
    #     if edition and series:                                                      # Check if edition or series exists
    #         newdir = rootdir+"/"+edition+"/Serie_"+series
    #
    #         title = df_json.display_title[js_i]
    #         files = [f for f in os.listdir(newdir)
    #                  if os.path.isfile(os.path.join(newdir, f))]                    # List all files in directory
    #         edit_distance = []
    #
    #         ## Compare file names in folder to file name from .json file
    #         for k in files:
    #             edit_distance = np.append(edit_distance,
    #                                       nltk.edit_distance(title, k,
    #                                                          substitution_cost=1, transpositions=False))
    #         # Get file name with closest resemblance (edit distance)
    #         filename = files[np.argmin(edit_distance)]      # Get file name
    #
    #         csv_index = df_dlcs.loc[df_dlcs["Origin"].str.contains(filename, case=False)]   # Get dlcs .csv data
    #         csv_uuid = csv_index.ID.values[0]               # Get uuid from .csv file
    #         url = dlcs_base+csv_uuid                        # Make URL where json for file can be found
    #         file_json = requests.get(url).json()            # Get .json file
    #         file_canvas = file_json["sequences"][0]["canvases"]
    #     else:
    #         print(str(js_i)+" is empty")

# image_corners = []
# for i in range(10):#len(df_json)):
#     if df_json.base_sheet[i]["region"]["geom4326"]:                             # Check if GEO info is available
#         edition = df_json.base_set[i]["edition"].replace(" ", "_").lower()       # Get edition number
#         series = df_json.base_set[i]["serie"]                                   # Get series number
#         newdir = rootdir+"/"+edition+"/Serie_"+series                           # Create directory to find map .jpg
#         title = df_json.display_title[i]                                        # Get file name of current map
#
#
#         files = [f for f in os.listdir(newdir)
#                  if os.path.isfile(os.path.join(newdir, f))]                    # List all files in directory
#         edit_distance = []                                                      # Empty array to find closest .jpg file
#
#         # Compare file names in folder to file name from .json file
#         for j in files:
#             edit_distance = np.append(edit_distance,
#                                       nltk.edit_distance(title, j,
#                                                          substitution_cost=1, transpositions=False))
#
#         # Get file name with closest resemblance (edit distance)
#         filename = files[np.argmin(edit_distance)]
#         fileloc = newdir+"/"+filename
#         im_coord = rect_coordinate.get_coordinate(fileloc)
#         # image_corners = np.dstack((image_corners, np.array(im_coord)))
#
#     else:
#         print("Geo location not available for:"+df_json.display_title[i])
#
