# -*- coding: utf-8 -*-
"""
Helper functions to decode structured data strored by django-hstore fields
"""
import json
import datetime
import numpy as np

import lxml.html.clean as clean

from django.utils import timezone


def json_loads_helper(obj):
    """Try convert given object into json"""
    try:
        return json.loads(obj)
    except (TypeError, ValueError):
        return obj


def parse_hstore_field(data):
    """Convert hstore value stored in database into python dictionary"""
    return dict(
        map(lambda (k, v): (k, json_loads_helper(v)), data.iteritems())
    )


def datetime_aware(data=None):
    """
    Make datetime object timezone aware.
    By default return timezone aware datatime.datetime.now()
    """
    if data is None:
        data = datetime.datetime.now()
    return timezone.make_aware(data, timezone.get_current_timezone())


def parse_pks(pks):
    """Method used to parse string with comma separated numbers"""
    output = []

    if isinstance(pks, (str, unicode)):
        for value in pks.split(','):
            try:
                value = int(value.strip())
            except ValueError:
                pass
            else:
                output.append(value)
    return output


def clean_html(value):
    """
    Clean html value and strip potentially dangerous code using
    :class:`lxml.html.clean.Cleaner`
    """
    cleaned = ''
    if value and value.strip():
        cleaner = clean.Cleaner(
            safe_attrs_only=True, safe_attrs=frozenset(['href'])
        )
        cleaned = cleaner.clean_html(value)
        # Cleaner wraps with p tag, it should be removed
        if cleaned.startswith('<p>') and cleaned.endswith('</p>'):
            cleaned = cleaned[3:-4]
    return cleaned


def df_to_geojson(df, properties, lat='latitude', lon='longitude'):
    geojson = {'type':'FeatureCollection', 'features':[]}
    for _, row in df.iterrows():
        feature = {'type':'Feature',
                   'properties':{},
                   'geometry':{'type':'Point',
                               'coordinates':[]}}
        feature['geometry']['coordinates'] = [row[lon],row[lat]]
        for prop in properties:
            feature['properties'][prop] = row[prop]
        geojson['features'].append(feature)
    return geojson


def aggregate_results(
    rdf, ddf, count_var, count_fun=np.sum,
    by_seq=False, seq_fun=np.max,
    by_loc=False, trate=True, merge_how='left'
):
    rdf[count_var] = rdf[count_var].fillna(0).astype(float)
    if by_seq:
        sin = rdf[rdf.sequence_id.isnull()]
        seq = rdf[~rdf.sequence_id.isnull()]
        sin.sequence_id = sin.sequence_id.fillna(-1)
        g1_sin = sin.groupby(
            ['deployment_id','sequence_id']
        )[count_var].aggregate(count_fun).reset_index()
        g1_seq = seq.groupby(
            ['deployment_id','sequence_id']
        )[count_var].aggregate(seq_fun).reset_index()
        g1 = g1_sin.append(g1_seq)
    else:
        g1 = rdf
    g2 = g1.groupby(
        ['deployment_id']
    )[count_var].aggregate(count_fun).reset_index()
    g2.columns = ['deployment_id', 'counts']
    out = ddf.merge(g2, how=merge_how, on='deployment_id')
    if by_loc:
        g3 = out.groupby(
            ['location_id']
        )['counts','days'].aggregate(count_fun).reset_index()
        out = g3.merge(out[['location_id','x','y']], how=merge_how, on='location_id')
        out.drop_duplicates(inplace=True)
    out.counts.fillna(0, inplace=True)
    if trate:
        out['trate'] = out.counts/out.days
        out.trate.fillna(0, inplace=True)
    return out

