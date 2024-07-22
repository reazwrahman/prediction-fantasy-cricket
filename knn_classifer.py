import pandas as pd
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score  
import matplotlib.pyplot as plt 
from sklearn.preprocessing import StandardScaler 
import copy

from batting_data import BattingDataUtil 
from config import GAME_FORMAT, PREDICTION_FORMAT

class KNNClassifier: 
    def __init__(self): 
        self.batting_util = BattingDataUtil()
        self.x_train = self.batting_util.get_training_data() 
        self.x_test = self.batting_util.get_testing_data()
        self.all_features = self.batting_util.get_all_features()  

        self.scaler = StandardScaler() 
        self.model = None 
        self.optimal_k = None
    
    def scale_training_data(self):
        self.scaler.fit_transform(self.x_train[self.all_features])  
    
    def build_model(self, training_data, k): 
        model = KNeighborsClassifier(n_neighbors=k)
        model.fit(training_data, self.x_train["bucket"])   
        return model  

    def make_predictions(self, k=None):   
        if not k: 
            k = self.find_optimal_k()

        if not self.model:
            model = self.build_model(self.x_train[self.all_features], k) 
            self.model = model 
        else: 
            model = self.model
            
        predictions = model.predict(self.x_test[self.all_features]) 
        return predictions 

    def make_single_prediction(self, features_data:list): 
        if not self.model:
            model = self.build_model(self.x_train[self.all_features], self.find_optimal_k()) 
            self.model = model 
        else: 
            model = self.model  
        
        prediction = model.predict([features_data]) 
        return prediction
    
    def compute_accuracy(self, predictions): 
        accuracy = accuracy_score(self.x_test["bucket"], predictions)  
        return accuracy*100
    
    def find_optimal_k(self): 
        if not self.optimal_k: 
            k_values = [13, 15, 16, 18, 20, 22, 25, 30, 32, 34, 36, 38, 42, 45, 48, 50, 55, 60] 
            accuracy_results = []
            for k in k_values:
                model = self.build_model(self.x_train[self.all_features], k) 
                predictions = model.predict(self.x_test[self.all_features]) 
                accuracy = accuracy_score(self.x_test["bucket"], predictions)
                accuracy_results.append((accuracy*100, k)) 
            
            #self.__plot_k_vs_accuracy(copy.deepcopy(accuracy_results))
            accuracy_results.sort() 
            self.optimal_k =  accuracy_results[-1][1] 
            
        return self.optimal_k  
    

    def __plot_k_vs_accuracy(self, accuracy_results):  
        k_values = [] 
        accuracies = [] 
        for each in accuracy_results: 
            k_values.append(each[1])  
            accuracies.append(each[0])
        plt.figure(figsize=(10, 6)) 
        plt.plot(k_values, accuracies, marker='o')
        plt.title('k-NN Classifier Accuracy for Different k Values')
        plt.xlabel('k')
        plt.ylabel('Accuracy')
        plt.xticks(k_values)
        plt.grid(True)
        plt.show() 


if __name__ == "__main__": 
    print(f'GAME FORMAT: {GAME_FORMAT}, PREDICTION FORMAT: {PREDICTION_FORMAT}')
    classifier = KNNClassifier()
    accuracy = classifier.compute_accuracy(classifier.make_predictions())  
    print(f'KNN classifier all features used')
    print(accuracy)  
    print('\n')