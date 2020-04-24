import streamlit as st
import json
from typing import List, Tuple, Dict
from dataclasses import dataclass
import requests
import pandas as pd
import datetime
from matplotlib import cm
from matplotlib import pyplot as plt


def normalize_province(p):
    corrected = {
        'Bangkok Metropolis': 'Bangkok',
        'Chon Buri': 'Chonburi',
        'Buri Ram': 'Buriram',
        'Lop Buri': 'Lopburi',
        'Prachin Buri': 'Prachinburi',
        'Phangnga': 'Phang Nga',
        'Nong Bua Lam Phu': 'Nong Bua Lamphu',
        'Si Sa Ket': 'Sisaket'
    }
    return corrected.get(p, p)


@dataclass
class ProvincePolygon:
    province: str
    geom_type: str
    coordinates: List[List[Tuple[float, float]]]

    @classmethod
    def from_geo_data(cls, geo_data) -> Dict[str, 'ProvincePolygon']:
        features = geo_data['features']
        ret = {}
        for feat in features:
            province = normalize_province(feat['properties']['name'])
            geom_type = feat['geometry']['type']
            coordinates = feat['geometry']['coordinates']
            ret[province] = ProvincePolygon(
                province=province,
                coordinates=coordinates,
                geom_type=geom_type
            )
        return ret

    def plot(self, **kwd):
        polygons = []
        if self.geom_type == 'Polygon':
            polygons.append(plt.Polygon(self.coordinates[0], **kwd))
        elif self.geom_type == 'MultiPolygon':
            for poly in self.coordinates:
                polygons.append(plt.Polygon(poly[0], **kwd))
        # print(len(polygons))
        for poly in polygons:
            plt.gca().add_patch(poly)


@st.cache(allow_output_mutation=True)
def get_province_polygons():
    url = 'https://github.com/apisit/thailand.json/raw/master/thailandWithName.json'
    raw = requests.get(url).text
    geo_data = json.loads(raw)
    return geo_data
    # return ProvincePolygon.from_geo_data(geo_data)


@st.cache
def get_daily_new_case_by_province():

    url2 = 'https://covid19.th-stat.com/api/open/cases'
    raw2 = requests.get(url2).json()

    df = pd.DataFrame(raw2['Data'])
    df['ConfirmDate'] = pd.to_datetime(df['ConfirmDate']).dt.date
    count_df = df.groupby(['ConfirmDate', 'ProvinceEn']).agg(
        {'No': 'count'}).reset_index()

    ret = {}
    for data in count_df.itertuples():
        if data.ConfirmDate not in ret:
            ret[data.ConfirmDate] = {}
        ret[data.ConfirmDate][data.ProvinceEn] = data.No
    return ret


pps = ProvincePolygon.from_geo_data(get_province_polygons())
new_cases = get_daily_new_case_by_province()

min_date = min(new_cases.keys())
max_date = max(new_cases.keys())
max_new_case = max(max(s.values()) for s in new_cases.values())
new_cases = get_daily_new_case_by_province()

date_shift = st.sidebar.slider('Date', 0, (max_date-min_date).days)
look_up_date = min_date+datetime.timedelta(days=date_shift)
st.sidebar.text(min_date+datetime.timedelta(days=date_shift))


def plot(lookup_date):
    #date = datetime.date(2020,4,3)
    plt.figure(figsize=(10, 10))
    cmap = cm.get_cmap('YlOrRd')
    for name, pp in pps.items():
        # print(pp.province)
        # print(pp.polygons)
        if look_up_date not in new_cases:
            new_case = 0
        else:
            new_case = new_cases[look_up_date].get(pp.province, 0)
        fc = cmap(min(new_case, 5)/5)
        pp.plot(ec='gray', fc=fc)
    plt.xlim(95, 110)
    plt.ylim(0, 25)
    plt.axis('equal')
    plt.axis('off')


total_new_case = 0
if look_up_date in new_cases:
    total_new_case = sum(new_cases[look_up_date].values())

f"# Total New Case for {look_up_date} = {total_new_case}"

plot(look_up_date)
st.pyplot()

if look_up_date in new_cases:
    new_case = new_cases[look_up_date]
    st.write(pd.DataFrame(
        {'province': list(new_case.keys()), 'new case': list(new_case.values())}))
else:
    st.write('No new case')
