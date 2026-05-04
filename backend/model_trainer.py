import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import pickle
import os

def create_dummy_data(samples=1000):
    # Generate some synthetic data
    # Features: cpu_usage, gpu_usage, vram_usage, frametime
    np.random.seed(42)
    cpu_usage = np.random.uniform(10, 100, samples)
    gpu_usage = np.random.uniform(10, 100, samples)
    vram_usage = np.random.uniform(10, 100, samples)
    
    # Calculate stutter probability based on a heuristic
    # High VRAM + High CPU = more likely to stutter
    stutter_prob = (vram_usage / 100) * 0.6 + (cpu_usage / 100) * 0.4
    
    # Add some noise
    stutter_prob += np.random.normal(0, 0.1, samples)
    
    # Target label: 1 if stutter, 0 if smooth
    target = (stutter_prob > 0.75).astype(int)
    
    # Frametime loosely correlates with the probability
    frametime = 16.6 + (target * np.random.uniform(10, 50, samples)) + np.random.normal(0, 1, samples)
    
    return pd.DataFrame({
        'cpu_usage': cpu_usage,
        'gpu_usage': gpu_usage,
        'vram_usage': vram_usage,
        'frametime': frametime,
        'target': target
    })

def train_model():
    print("Generating synthetic telemetry data...")
    df = create_dummy_data(5000)
    
    X = df[['cpu_usage', 'gpu_usage', 'vram_usage', 'frametime']]
    y = df['target']
    
    print("Training Random Forest model...")
    model = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
    model.fit(X, y)
    
    # Save the model
    os.makedirs('model_output', exist_ok=True)
    with open('model_output/rf_model.pkl', 'wb') as f:
        pickle.dump(model, f)
        
    print("Model saved to model_output/rf_model.pkl")

if __name__ == "__main__":
    train_model()
