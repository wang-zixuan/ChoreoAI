import torch
from os import path as osp
import logging
import numpy as np
from torch.utils.data import Subset, DataLoader

from utils.logger import get_root_logger
from utils.misc import get_time_str
from data.dataset import DancerDataset
from model.model_pipeline import Pipeline

def init_logger():
    log_file = osp.join("log", f"train_{get_time_str()}.log")
    logger = get_root_logger(
        logger_name='ai_choreo', log_level=logging.INFO, log_file=log_file)

    return logger


def preprocess_dataset(dancer_np):
    dancer1_np = dancer_np[::2, :, :]
    dancer2_np = dancer_np[1::2, :, :]
    return dancer1_np, dancer2_np


def create_dataset_loader(dataset_dir):
    dancer_np = np.load('dataset/' + dataset_dir)
    dancer1_np, dancer2_np = preprocess_dataset(dancer_np)
    dataset = DancerDataset(torch.from_numpy(dancer1_np), torch.from_numpy(dancer2_np), 64)

    train_size = int(0.7 * len(dataset))
    validation_size = int(0.2 * len(dataset))

    train_dataset = Subset(dataset, range(train_size))
    validation_dataset = Subset(dataset, range(train_size, train_size + validation_size))

    train_loader = DataLoader(train_dataset, batch_size=16, shuffle=False)
    validation_loader = DataLoader(validation_dataset, batch_size=1, shuffle=False)
    return train_loader, validation_loader


def main():
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True

    logger = init_logger()

    dataset_names = ['pose_extraction_img_9085.npy', 'pose_extraction_ilya_hannah_dyads.npy', 'pose_extraction_hannah_cassie.npy', 'pose_extraction_dyads_rehearsal_leah.npy']

    train_loaders = []
    validation_loaders = []
    
    train_losses = []
    validation_losses = []

    for name in dataset_names:
        train_loader, validation_loader = create_dataset_loader(name)
        train_loaders.append(train_loader)
        validation_loaders.append(validation_loader)

    epochs = 100

    logger.info("Started training.")

    model = Pipeline()

    prev_best_validation_loss = -1

    for epoch in range(epochs):
        logger.info(f"Epoch: {epoch}")
        for train_loader in train_loaders:
            logger.info(f"train loader size: {len(train_loader)}")
            for train_data in train_loader:
                model.feed_data(train_data)
                cur_loss = model.optimize_parameters()
                train_losses.append(cur_loss.item())
                logger.info(f"training loss: {cur_loss}")

        model.update_learning_rate()

        validation_loss = 0

        for validation_loader in validation_loaders:
            validation_loss += model.test(validation_loader)
        
        validation_loss /= len(validation_loaders)
        validation_losses.append(validation_loss.item())

        if prev_best_validation_loss == -1 or validation_loss < prev_best_validation_loss:
            prev_best_validation_loss = validation_loss
            model.save_network()
    
    np.save("train_loss_" + get_time_str() + ".npy", np.array(train_losses))
    np.save("validation_loss_" + get_time_str() + ".npy", np.array(validation_losses))


if __name__ == '__main__':
    main()
