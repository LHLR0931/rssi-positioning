import os, sys
sys.path.insert(0, os.path.dirname(__file__))

import argparse
import pytorch_lightning as pl
from pytorch_lightning.callbacks import ModelCheckpoint,EarlyStopping,LearningRateMonitor

# 训练的话注释，否则报找不到包的错误
# from api.deeplearning.WiFiRSSICNNModel import WiFiRSSICNNModel
# from api.deeplearning.WiFiRSSICNNDataModule import WiFiRSSICNNDataModule


# 启用django 的话注释，否则报找不到包的错误。训练的话不注释
from WiFiRSSICNNModel import WiFiRSSICNNModel
from WiFiRSSICNNDataModule import WiFiRSSICNNDataModule


from pytorch_lightning.loggers import TensorBoardLogger
import torch
import os


def train_model(args):
    # Load the data
    data_module = WiFiRSSICNNDataModule(batch_size=args.batch_size, num_workers=args.num_workers,db_path=args.db_path)
    # model
    model = WiFiRSSICNNModel(
        output_size=2,
        learning_rate=args.learning_rate
    )
    # Callbacks
    # checkpoint_callback = ModelCheckpoint(
    #     monitor='val_loss',
    #     dirpath='./cnn_checkpoints',
    #     filename='wifi-rssi-{epoch:02d}-{val_loss:.2f}',
    #     save_top_k=1,
    #     mode='min',
    #     save_last=True
    # )
    # # Early stopping
    # early_stopping = EarlyStopping(
    #     monitor='val_loss',
    #     min_delta=0.001,
    #     patience=10,
    #     verbose=True
    # )
    checkpoint_callback = ModelCheckpoint(
        monitor='train_loss_epoch',
        dirpath='./cnn_checkpoints',
        filename='wifi-rssi-{epoch:02d}-{train_loss_epoch:.2f}',
        save_top_k=1,
        mode='min',
        save_last=True
    )   

    early_stopping = EarlyStopping(
        monitor='train_loss_epoch',
        min_delta=0.001,
        patience=10,
        verbose=True,
        mode='min'
    )

    lr_monitor = LearningRateMonitor(logging_interval='epoch')


    logger = TensorBoardLogger(
        save_dir="./logs",
        name="wifi-rssi-positioning"
    )

    # Check if GPU is available and set the accelerator accordingly
    # accelerator = 'gpu' if torch.cuda.is_available() else 'cpu'
    accelerator = 'cpu'
    trainer = pl.Trainer(
        accelerator=accelerator,
        # devices=1 if accelerator == 'gpu' else None,
        max_epochs=args.max_epochs,
        callbacks=[checkpoint_callback, early_stopping, lr_monitor],
        logger=logger
    )

    # Train the model
    trainer.fit(model, data_module)
    # Test the model
    #trainer.test(model,data_module)
    trainer.test(ckpt_path="best", datamodule=data_module)

    return model



def predict(model_path, X_pred):
    device = torch.device("cpu")
    # Load the trained model
    model = WiFiRSSICNNModel(output_size=2)
    # Ensure model loads to the appropriate device
    model.load_state_dict(torch.load(model_path, map_location=device)['state_dict'])
    model.to(device)                                  # ← 新增1：模型放到同一设备
    model.eval()

    X_pred_array = X_pred.to_numpy()
    X_pred = torch.tensor(X_pred_array, dtype=torch.float32, device=device)  # ← 新增2：数据放到同一设备
    # Make predictions
    with torch.no_grad():
        y_pred = model(X_pred)
    return y_pred.detach().cpu().numpy()

def cnn_train(num_workers=4):
    parser = argparse.ArgumentParser(description='WiFi RSSI Positioning')
    parser.add_argument('--batch_size', type=int, default=8, help='Batch size')
    parser.add_argument('--num_workers', type=int, default=4, help='Number of worker processes for data loading')
    parser.add_argument('--hidden_size', type=int, default=256, help='Size of the hidden layer')
    parser.add_argument('--learning_rate', type=float, default=1e-3, help='Learning rate')
    parser.add_argument('--max_epochs', type=int, default=100, help='Maximum number of epochs')
    parser.add_argument('--db_path', type=str, default=os.path.join(os.getcwd(), 'db_new.sqlite3'), help='Path to the SQLite database file')
    # parser.add_argument('--db_path', type=str, default=os.getcwd()+'/db.sqlite3', help='Path to the SQLite database file')
    args = parser.parse_args()
    print("Using database:", args.db_path)
    model = train_model(args)

if __name__ == '__main__':
    cnn_train()

    # # Prediction example
    # X_pred = create_prediction_vector(averaged_wifi_data, data_module.unique_bssids)
    # predictions = predict(args, model, X_pred)
    # print(predictions)