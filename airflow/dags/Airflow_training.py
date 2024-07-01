from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
import os
import torch
import shutil



def load_checkpoint(filepath):
    if os.path.isfile(filepath):
        checkpoint = torch.load(filepath)
        return checkpoint
    else:
        print(f"No checkpoint found at '{filepath}'")
        return None

def print_and_compare_losses(checkpoint1, checkpoint2):
    if checkpoint1 is not None and checkpoint2 is not None:
        print("Checkpoints loaded.")

        losses1 = {
            'Steps': checkpoint1['steps'],
            'Epoch': checkpoint1['epoch'],
            'Best Validation Classification Loss': checkpoint1['best_val_cls_loss'],
        }

        losses2 = {
            'Steps': checkpoint2['steps'],
            'Epoch': checkpoint2['epoch'],
            'Best Validation Classification Loss': checkpoint2['best_val_cls_loss'],
        }

        print(f"\nCheckpoint 1: {losses1}")
        print(f"Checkpoint 2: {losses2}")

        for key in losses1:
            if key in losses2:
                diff = losses1[key] - losses2[key]
                print(f"Difference in {key}: {diff}")

        # Determine which checkpoint is better
        best_checkpoint = 'model_chkpt_250.pt' if losses1['Best Validation Classification Loss'] < losses2['Best Validation Classification Loss'] else 'model_chkpt_best.pt'
        return best_checkpoint
    else:
        print("One or both checkpoints are missing.")
        return None

def replace_model(best_checkpoint, save_dir):
    current_model_path = os.path.join(save_dir, 'current_model.pt')
    best_model_path = os.path.join(save_dir, best_checkpoint)

    if os.path.isfile(best_model_path):
        shutil.copyfile(best_model_path, current_model_path)
        print(f"Replaced current model with {best_checkpoint}")
    else:
        print(f"No model file found at {best_model_path}")

def compare_and_replace_checkpoints():
    # Set the path to your model checkpoints
    save_dir = 'models_detr/new_model'
    checkpoint1_path = os.path.join(save_dir, 'model_chkpt_250.pt')
    checkpoint2_path = os.path.join(save_dir, 'model_chkpt_best.pt')

    # Load the checkpoints
    checkpoint1 = load_checkpoint(checkpoint1_path)
    checkpoint2 = load_checkpoint(checkpoint2_path)

    # Print and compare the losses
    best_checkpoint = print_and_compare_losses(checkpoint1, checkpoint2)

    # Replace the current model with the best checkpoint
    if best_checkpoint:
        replace_model(best_checkpoint, save_dir)

# Define default_args dictionary with default parameters for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Define the DAG
with DAG(
    'compare_and_replace_checkpoints',
    default_args=default_args,
    description='A DAG to train the model, compare checkpoint losses, and replace the current model with the best checkpoint',
    schedule_interval=timedelta(days=1),
    start_date=datetime(2023, 6, 23),
    catchup=False,
) as dag:

    # Task 1: Train the model
    t1 = BashOperator(
        task_id='train_model',
        bash_command='python /opt/airflow/BirdSoundClassif/train.py', 
    )

    # Task 2: Compare checkpoints and replace the model
    t2 = PythonOperator(
        task_id='compare_and_replace_checkpoints_task',
        python_callable=compare_and_replace_checkpoints,
    )

    # Set task dependencies
    t1 >> t2