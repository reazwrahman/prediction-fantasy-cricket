import pandas as pd 
import numpy as np  
from sklearn.preprocessing import LabelEncoder 
from sklearn.preprocessing import StandardScaler 
import copy


from config import DATA_FILES, GAME_FORMAT, PREDICTION_FORMAT

class BattingDataGenerator: 
    def __init__(self, filenames): 
        self.filenames = filenames  
        self.df = None  
        self.n = 5 ## look at recent n matches for current form 
        self.initialize()

    def initialize(self):
        ## procedures 
        self.generate_raw_dfs() 
        self.do_basic_cleanup() 
        self.apply_bucket()  
        self.calculate_average_runs() 
        self.calculate_recent_average() 
        self.calculate_average_sr() 
        self.calculate_recent_sr() 
        self.df = self.df.dropna()
    
    def generate_raw_dfs(self):  
        self.raw_dfs = []  
        for i in range (len(self.filenames)):
            df = pd.read_csv(self.filenames[i]) 
            batting_columns = ['Innings Player', 'Innings Runs Scored Num','Innings Not Out Flag',
                'Innings Balls Faced', 'Innings Batting Strike Rate', 'Opposition', 'Ground', 'Innings Date', 'Country',
                'Innings Runs Scored Buckets']
            
            df = df[batting_columns]  
            new_batting_column = ['player', 'runs','not_out_flag',
                'balls_faced', 'strike_rate', 'opposition', 'ground', 'date', 'country',
                'bucket'] 
            
            df.columns = new_batting_column 
            self.raw_dfs.append(df) 
            self.df = pd.concat(self.raw_dfs, ignore_index=True)  
    

    def do_basic_cleanup(self):
        self.df.replace('-', np.nan, inplace=True)
        self.df = self.df.dropna(subset=['runs'])   
        self.df['opposition'] = self.df['opposition'].str.replace('^v ', '', regex=True)
        self.df['date'] = pd.to_datetime(self.df['date']) 

        self.df['runs'] = self.df['runs'].astype(int) 
        self.df['not_out_flag'] = self.df['not_out_flag'].astype(int)  
        self.df['strike_rate'] = self.df['strike_rate'].astype(float)  

        self.df['year'] = self.df['date'].apply(lambda row: row.year) 
    

    def apply_bucket(self):  
        if PREDICTION_FORMAT == "BINARY":
            self.df['bucket'] = self.df['runs'].apply(self.__use_binary_classifier)   
        elif PREDICTION_FORMAT == "CUSTOM": 
            self.df['bucket'] = self.df['runs'].apply(self.__use_custom_classifier)

    def calculate_average_runs(self): 
        grouped = self.df.groupby('player').agg(
        total_runs=pd.NamedAgg(column='runs', aggfunc='sum'),
        innings_count=pd.NamedAgg(column='not_out_flag', aggfunc=lambda x: (x == 0).sum())
        ).reset_index()
    
        grouped['avg_runs'] = round(grouped['total_runs'] / grouped['innings_count'],2) 
        
        # Replace infinite values with the total_runs values (involves domain knowledge of cricket)
        grouped['avg_runs'] = grouped.apply(
            lambda row: row['total_runs'] if np.isinf(row['avg_runs']) else row['avg_runs'], axis=1
        )
        self.df = pd.merge(self.df, grouped[['player', 'avg_runs']], on='player')  
        self.df['avg_runs'] = pd.to_numeric(self.df['avg_runs'], errors='coerce') 
    

    def calculate_recent_average(self): 
        # Sort DataFrame by 'Player' and 'Innings Date'
        self.df = self.df.sort_values(by=['player', 'date'], ascending=[True, False])

        # Group by 'Player' and take the latest 'n' matches
        df_latest_n = self.df.groupby('player').head(self.n)

        # Group by 'Player' and calculate total runs and valid innings count
        grouped = df_latest_n.groupby('player').agg(
            total_runs=pd.NamedAgg(column='runs', aggfunc='sum'),
            innings_count=pd.NamedAgg(column='not_out_flag', aggfunc=lambda x: (x == 0).sum())
        ).reset_index()

        # Calculate average runs
        grouped['recent_avg'] = grouped['total_runs'] / grouped['innings_count']

        # Replace inf values with the total_runs values
        grouped['recent_avg'] = grouped.apply(
            lambda row: row['total_runs'] if np.isinf(row['recent_avg']) else row['recent_avg'], axis=1
        )

        # Merge the average runs back into the original DataFrame
        self.df = pd.merge(self.df, grouped[['player', 'recent_avg']], on='player', how='left')



    def calculate_average_sr(self):  
        ## replace nan strike rate to a reasonable value 
        self.df['strike_rate'] = self.df.apply(lambda row: row['runs']*100 if pd.isna(row['strike_rate']) else row['strike_rate'], axis=1)
        self.df['strike_rate'] = pd.to_numeric(self.df['strike_rate'], errors='coerce')
        average_sr = self.df.groupby('player')['strike_rate'].mean().reset_index()
        average_sr.columns = ['player', 'avg_sr']
        self.df = pd.merge(self.df, average_sr, on='player')  
        self.df['avg_sr'] = round(self.df['avg_sr'],2) 

    
    def calculate_recent_sr(self):  
        df_latest_n = self.df.groupby('player').head(self.n)
        recent_avg_sr = df_latest_n.groupby('player')['strike_rate'].mean().reset_index() 
        recent_avg_sr.columns = ['player','recent_avg_sr']
        self.df = pd.merge(self.df, recent_avg_sr, on='player') 
        self.df['recent_avg_sr'] = round(self.df['recent_avg_sr'],2)



    def __use_custom_classifier(self, runs):
        if runs >=0 and runs <=25: 
            return '0-25' 
        elif runs > 25 and runs <=50: 
            return '25-50' 
        elif runs > 50  and runs <=75: 
            return '50-75'  
        elif runs > 75 and runs <=100: 
            return '75-100'
        else: 
            return '100+'
    
    def __use_binary_classifier(self, runs):
        if runs >=0 and runs <=30: 
            return 'no pick' 
        else: 
            return 'pick'


class BattingDataUtil: 
    def __init__(self): 
        self.testing_files = DATA_FILES[GAME_FORMAT]["testing_files"] 
        self.training_files = DATA_FILES[GAME_FORMAT]["training_files"] 
        self.training_data_generator = BattingDataGenerator(filenames=self.training_files)
        self.testing_data_generator = BattingDataGenerator(filenames=self.testing_files) 

        self.training_df = self.training_data_generator.df 
        self.testing_df = self.training_data_generator.df  
    
        self.selected_features=['opposition','ground', 'country', 'avg_runs', 'recent_avg', 
                   'avg_sr', 'recent_avg_sr']
        
        self.initialize()
    
    def get_all_features(self): 
        return copy.deepcopy(self.selected_features)

    def get_training_data(self): 
        return self.training_df 
    
    def get_testing_data(self): 
        return self.testing_df
    
    def initialize(self): 
        self.training_df = self.__encode_data(self.training_data_generator.df) 
        self.testing_df = self.__encode_data(self.testing_data_generator.df) 

    
    def __encode_data(self, df): 
        ## encode features 
        le = LabelEncoder()
        df['opposition'] = le.fit_transform(df['opposition']) 
        df['ground'] = le.fit_transform(df['ground'])
        df['country'] = le.fit_transform(df['country']) 
        df['bucket'] = le.fit_transform(df['bucket']) 
        return df 
        


if __name__ == "__main__":  
   batting_util = BattingDataUtil() 
   print ('training data below: ') 
   print(batting_util.get_training_data()) 
   print ('\n') 

   print ('testing data below: ') 
   print(batting_util.get_testing_data()) 
   print ('\n')


    

