import eurostat
from neo4j import GraphDatabase, basic_auth
import neo4j
import pandas as pd
import numpy as np
import time
import os
from dotenv import load_dotenv
from pathlib import Path
import pycountry

database_name = os.getenv('DATABASE_NAME')

def write_indicators(tx,statement, params_dict):
    tx.run(statement, parameters=params_dict)

def write_batch(tx,statement, params_list):
    tx.run(statement, parameters={"parameters": params_list})

##preprocessing eurostat codes
def preprocessing_eurostat_data(code,available_geoCodes,is_local_level=False,filtering_params=None):
    '''
    Input: the EU SDG indicator code
    Output: the dataframe after preprocessing of the data   
    '''
    
    print()
    print("Indicator code: ",code)
    print()
    # Read dataset of sdg_code from the main database and returns it as a pandas dataframe
    if filtering_params:
        #df_code = eurostat.get_data_df(code, filter_pars=filtering_params)
        df_code = eurostat.get_data_df(str(code), filter_pars=filtering_params) 
    else:
        df_code = eurostat.get_data_df(code)
    df_code.columns= map(str.lower,df_code.columns)

    # Subset of dataframe based on type of columns (only select years or age)
    columns_years = [col for col in df_code.columns if all(char.isdigit() for char in col)]
    
    # Delete '\\'
    for col in list(df_code.columns):
        if '\\' in col:
            new_name = col.split('\\')
            df_code = df_code.rename(columns={col: new_name[0]})
    
    # Subset of dataframe (only select dimensions,attributes & geo)
    columns_att_dim_geo = list(set(df_code.columns) - set(columns_years))

    if 'geo' in columns_att_dim_geo:

        if is_local_level:
            # Keep only NUTS Level
            df_code['NUTS_length'] = df_code['geo'].map(str).map(len)

            # Keep only the rows with NUTS codes
            df_code = df_code.loc[df_code['NUTS_length'].isin([3,4,5])]

            # Drop column NUTS Level
            df_code.drop(['NUTS_length'],axis=1,inplace=True)

        # Unpivot dataframe
        df = pd.melt(df_code,id_vars=list(columns_att_dim_geo),var_name='time',value_name='value')

        # Drop NA values
        print('Length of df before removing NA values:',len(df))
        df = df.dropna()
        print('Length of df after removing NA values:',len(df))

        # Keep only the rows containing values of countries existing in the neo4j LPG model.
        df = df[df['geo'].isin(available_geoCodes)]
        print('Length of df after selecting only areas existing in neo4j SustainGraph:',len(df))


        # Select only the dimensions columns
        cols = list(df[df.columns.difference(['unit','geo','value','time'])].columns)
        print()
        print('Columns of df:', list(df.columns))
        print('Dimension columns:', cols)
        print()

        # Condition: if the df's columns contain 'unit' column then create a dictionary eu_dimensions
        # in which keys are the dimensions codes and values are the description of the dimensions
        if cols:
            for col in cols:
                dict1= eurostat.get_dic(code,col)
                dict_col = dict(dict1)
                df[col+'_desc'] = df[col].map(dict_col)

            cols_desc = [item + '_desc' for item in cols]

            # Create dimensions_code and dimensions_description columns
            df['dim_codes'] = df[cols].apply(lambda row: '|'.join(row.values.astype(str)), axis=1)
            df['dim_desc'] = df[cols_desc].apply(lambda row: '|'.join(row.values.astype(str)), axis=1)

            # Drop dimensions columns
            df.drop(cols+cols_desc,axis=1,inplace=True)

        else:
            df['dim_codes']='NA'
            df['dim_desc'] = 'Not available'

        # Condition: if unit in the df's column, then create the att_desc column based on the mapping of the eurostat
        # codes
        eu_dimensions_unit = {}
        if 'unit' in df.columns:

            print('Attribute columns: unit')
            print()

            eu_attributes = eurostat.get_dic(code,'unit')
            eu_dimensions_unit = dict(eu_attributes)
            df['att_desc'] = df['unit'].map(eu_dimensions_unit)
            df.rename(columns = {'unit':'att_codes'}, inplace = True)

        else:
            print('Attribute columns: Not exists')
            print()
            df['att_desc'] = 'Not Available'
            df['att_codes'] = 'NA'

        print('----------------------------------------------------------')

        df.reset_index(inplace=True,drop=True)

        return df
    
    else:
        return None


## import to neo4j   
def import_sm_obs(df,indicator_code,batch_size,driver,geoEUcode=True):
    '''
    Input:  df: dataframe after preprocessing, 
            indicator_code: code of the corresponding Indicator,
            batch size: batch size to commit data in the neo4j LPG
    '''    


    # Create SeriesMetadata nodes in the neo4j only if dont exist
    df_sm = df[['dim_codes','att_codes','dim_desc','att_desc']].drop_duplicates()

    statement_sm = """
                MATCH (s:Series{code:$s_code})
                MERGE (sm:SeriesMetadata{attributesCode:$att_code,dimensionsCode:$d_code,
                                        attributesDescription:$att_desc,dimensionsDescription:$dim_desc,
                                        seriesCode: $s_code})
                MERGE (s)-[:HAS_METADATA]->(sm)  
                """ 

    # Create Observation nodes in the neo4j and commit result in batches.
    if geoEUcode:
        statement_obs = """
        UNWIND $parameters as row
        MATCH (ga:GeoArea),(sm:SeriesMetadata{attributesCode:row.att,dimensionsCode:row.dim,seriesCode:row.code}),
        (i:Indicator{code:row.code})
        WHERE row.geo = ga.EUcode
        MERGE (sm)-[:HAS_OBSERVATION{attributesCode:row.att,dimensionsCode:row.dim,seriesCode:row.code,time:date(row.year),geoCode:row.geo}]->(o:Observation{time:date(row.year)})
        MERGE (o)-[:REFERS_TO_AREA]->(ga)
        SET o.value = toFloat(row.value)
        MERGE (i) -[:HAS_OBSERVATIONS]->(ga)
        """
    else:
        statement_obs = """
        UNWIND $parameters as row
        MATCH (ga:GeoArea),(sm:SeriesMetadata{attributesCode:row.att,dimensionsCode:row.dim,seriesCode:row.code}),
        (i:Indicator{code:row.code})
        WHERE row.geo = ga.ISOalpha3code
        MERGE (sm)-[:HAS_OBSERVATION{attributesCode:row.att,dimensionsCode:row.dim,seriesCode:row.code,time:date(row.year),geoCode:row.geo}]->(o:Observation{time:date(row.year)})
        MERGE (o)-[:REFERS_TO_AREA]->(ga)
        SET o.value = toFloat(row.value)
        MERGE (i) -[:HAS_OBSERVATIONS]->(ga)
        """

    with driver.session(database=database_name) as session:  
        for index, row in df_sm.iterrows():
            
            
            session.execute_write(write_indicators, 
                                params_dict = {
                                    'att_code':str(row['att_codes']),
                                    'd_code':str(row['dim_codes']),
                                    'att_desc':str(row['att_desc']),
                                    'dim_desc':str(row['dim_desc']),
                                    's_code':indicator_code},
                                statement = statement_sm)

    params=[]
    batch_size = batch_size
    batch_i = 1

    with driver.session(database=database_name) as session:
        for index, row in df.iterrows():
            params_dict = {
                'geo': str(row['geo']), 
                'year': str(row['time']),
                'value': float(row['value']),
                'code':str(indicator_code),
                'att':str(row['att_codes']),
                'dim': str(row['dim_codes'])
            }
            params.append(params_dict)
            if index % batch_size == 0 and index > 0:
                st = time.time()
                session.execute_write(write_batch, params_list = params,statement = statement_obs)
                # driver.execute_query(statement,parameters=params)
                et = time.time()
                # get the execution time
                elapsed_time = et - st            
                print('Batch {} with {} observations : Done! ({} minutes)'.format(batch_i,len(params),elapsed_time/60))
                params = []            
                batch_i +=1

        if params:
            st = time.time()  # Record start time for the last batch
            session.execute_write(write_batch, params_list=params, statement=statement_obs)
            et = time.time()
            elapsed_time = et - st
            print('{} observations: Done! ({} minutes)'.format(len(params), elapsed_time/60))


## Happiness functions
def country_code_converter(input_countries):
    """
    :param input_countries: list containing the name of the countries (can be numpy array)
    :return: list with the ISO alpha 3 codes for the given input ('Unknown Country' if no match found)
    """
    countries = {}
    countries_official = {}
    countries_common = {}

    #loops over all of the countries contained in the pycountry library and populates dictionary
    for country in pycountry.countries:
        countries[country.name] = country.alpha_3

    #loops over the alpha_3 codes from the countries dictionary
    #populates dictionary containing official names and codes
    for alpha_3 in list(countries.values()):
        try:
            countries_official[pycountry.countries.get(alpha_3 = alpha_3).official_name] = alpha_3
        except:
            None
    #same for common names
    for alpha_3 in list(countries.values()):
        try:
            countries_common[pycountry.countries.get(alpha_3 = alpha_3).common_name] = alpha_3
        except:
            None

    codes = []
    # appends ISO codes for all matches by trying different country name types
    # appends Unknown Country if no match found
    for i in input_countries:
        if i in countries.keys():
            codes.append(countries.get(i))

        elif i in countries_official.keys():
            codes.append(countries_official.get(i))

        elif i in countries_common.keys():
            codes.append(countries_common.get(i))

        else:
            codes.append(None)
    return codes

def preprocessing_happiness(path,sheetname,driver):
    # Read excel file
    df_hap = pd.read_excel(path, sheet_name=sheetname)
    
    # Return geo column
    column_geo = list(filter(lambda x: 'Country' in x, list(df_hap.columns)))[0]
    
    # Apply only to 2022 data
    df_hap[column_geo] = df_hap[column_geo].str.replace("*","")
    list_countries_hap = list(df_hap[column_geo].unique())
    
    countries = {}
    for i,country in enumerate(list_countries_hap):
        countries[country] =  country_code_converter(list_countries_hap)[i]

    # Missing    
    missing = [k for k,v in countries.items() if v==None]
    print('Before update: No codes of countries:',missing)

    # Update dict
    upd_dict ={'Kosovo':None,
     'North Cyprus':None,
     'Russia':'RUS',
     'Hong Kong S.A.R. of China':'HKG',
     'Ivory Coast':'CIV',
     'Laos':'LAO',
     'Iran':'IRN',
     'Palestinian Territories':'PSE',
     'Eswatini, Kingdom of':None,
     'Congo (Brazzaville)':'COG',
     'Swaziland':'SWZ'}
    countries.update(upd_dict)

    # Missing
    mis = [k for k,v in countries.items() if v==None]
    print()
    print('After update: No codes of countries:',mis)
    
    # Add code to df
    df_hap['Country_code'] = df_hap[column_geo].map(countries)
    
    # Drop NA values
    print('Length (with NA values):',len(df_hap))
    df_hap.dropna(inplace=True)
    print('Length (without NA values):',len(df_hap))

    
    # Select only the geoAreas in the SustainGraph using a cypher query that returns the geocodes from the 
    # neo4j LPG.
    records, summary, keys = driver.execute_query("""
        MATCH (r:Region{name:'Europe'})-[:HAS_SUBREGION]->(sr:SubRegion)-[:HAS_AREA]->(a:Area)
        MATCH (eu:EuropeanUnion)<-[:BELONGS_TO]-(eua:Area)
        WITH COLLECT(DISTINCT a.ISOalpha3code)+COLLECT(DISTINCT eua.ISOalpha3code) as geocodes
        UNWIND geocodes as codes
        RETURN COLLECT(DISTINCT codes) as geocodes
        """,routing_="r")
    available_neo4j_geocodes = records[0]['geocodes']

    # Keep only the rows containing values of countries existing in the neo4j LPG model.
    df_hap = df_hap.loc[df_hap['Country_code'].isin(available_neo4j_geocodes)]
    print('Length of df after selecting only countries existing in neo4j SustainGraph:',len(df_hap))
    print('---------------------------------------------------------------------------')
    # Select columns
    selected_columns = list(filter(lambda x: 'Country' in x or 'Explained' in x or 'Happiness ' in x 
                         or 'residual' in x, list(df_hap.columns)))
    df_hap = df_hap[selected_columns]
    
    return df_hap

def import_happiness_score(df,year,series_encoding,batch_size,driver):
        
    # Filter only the columns of the df that contains 'Explained' or 'Residual' or 'Happiness'
    series = list(filter(lambda x: 'Explained' in x or 'residual' in x or 'Happiness' in x, list(df.columns)))
    print(year)
    # Default values
    url = 'https://worldhappiness.report/archive/'
    code_name = 'happiness_score'

    # Create Indicator,Series and Series_metadata
    statement_i_s_sm = """
    MATCH (so:Source{name:'TPS'})
    MERGE (i:Indicator{code:$ind_code,description:$ind_desc})
    MERGE (i)-[:COMES_FROM]->(so)
    MERGE (s:Series{code:$s_code,dataProviderURL:$url,description:'Happiness  Score: ' + $s_desc})
    MERGE (i)-[:HAS_SERIES]->(s)
    MERGE (sm:SeriesMetadata{attributesCode:'CLS',
                            dimensionsCode:'A',
                            attributesDescription:'Cantril Ladder Score',
                            dimensionsDescription:'Annual',
                            seriesCode : $s_code})
    MERGE (s)-[:HAS_METADATA]->(sm)
    """

    statement_hap_obs = """
        
    UNWIND $parameters as row
    MATCH (ga:GeoArea),(sm:SeriesMetadata{attributesCode:row.att,dimensionsCode:row.dim,seriesCode:row.code}),
    (i:Indicator{code:row.ind_code})
    WHERE row.geo = ga.ISOalpha3code
    MERGE (sm)-[:HAS_OBSERVATION{attributesCode:row.att,dimensionsCode:row.dim,seriesCode:row.code,time:date(row.year),geoCode:row.geo}]->(o:Observation{time:date(row.year)})
    MERGE (o)-[:REFERS_TO_AREA]->(ga)
    SET o.value = toFloat(row.value)
    MERGE (i) -[:HAS_OBSERVATIONS]->(ga)
    """
    batch_size = batch_size
    batch_i = 1
    params=[]
    with driver.session(database=database_name) as session:
        for s in series:
            ind_description = 'The World Happiness Report is a publication of \
                the United Nations Sustainable Development Solutions Network.\
                It contains articles and rankings of national happiness, \
                based on respondent ratings of their own lives,which the report \
                also correlates with various (quality of) life factors.'
            # If we are going to import data related to happiness score then we keep the above description.
            # Otherwise the format of the description is 'Happiness_score' + explained by variable
            description = ind_description if s == 'Happiness score' else str(s)
            
            session.execute_write(write_indicators, 
                            params_dict = {
                                'ind_code':code_name,
                                'ind_desc':ind_description,
                                'url':url,
                                's_code':series_encoding[s],
                                's_desc':description},
                            statement = statement_i_s_sm)
            print(series_encoding[s])
            params=[]
            for index, row in df.iterrows():
                params_dict = {
                    'ind_code':code_name,
                    'geo': str(row['Country_code']), 
                    'year': year ,
                    'value': float(row[s]),
                    'code':series_encoding[s],
                    'att':'CLS',
                    'dim': 'A'
                    }
                params.append(params_dict)
                if index % batch_size == 0 and index > 0:
                    st = time.time()
                    session.execute_write(write_batch, params_list = params,statement = statement_hap_obs)
                    et = time.time()
                    # get the execution time
                    elapsed_time = et - st            
                    print('Batch {} with {} observations : Done! ({} minutes)'.format(batch_i,len(params),elapsed_time/60))
                    params = []            
                    batch_i +=1

            if params:
                st = time.time()  # Record start time for the last batch
                session.execute_write(write_batch, params_list=params, statement=statement_hap_obs)
                et = time.time()
                elapsed_time = et - st
                print('{} observations: Done! ({} minutes)'.format(len(params), elapsed_time/60))

