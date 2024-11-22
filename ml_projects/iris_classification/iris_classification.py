import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.svm import LinearSVC

def train():
    columns = ['Sepal length', 'Sepal width', 'Petal length', 'Petal width', 'Class_labels'] 
    # Load the data
    df = pd.read_csv('./ml_projects/iris_classification/iris.data', names=columns)

    # Separate features and target  
    data = df.values
    X = data[:,0:4]
    Y = data[:,4]

    # Train the model
    X_train, X_test, y_train, y_test = train_test_split(X, Y, test_size=0.2)

    svn = LinearSVC()
    svn.fit(X_train, y_train)

    # Predict from the test dataset
    predictions = svn.predict(X_test)
    return accuracy_score(y_test, predictions)

if __name__ == "__main__":
    train()