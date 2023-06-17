import numpy as np
import matplotlib.pyplot as plt
import torch 
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from scipy.stats import norm
import preprocessing as pre

def visualize(vae_model, input_tensor, device):
    """
    Visualize the input and the output of the VAE model.

    Parameters:
    -----------
    `vae_model` : VAE object, the trained VAE model
    `input` : tensor, the input images.
    `device` : torch.device, the device to use for predicting
    """
    input = input_tensor.cpu().detach().numpy()
    output_tensor = vae_model.predict( input_tensor, device )
    output = output_tensor.cpu().detach().numpy()
    
    for i in range(0, len(input)):
        fig, axs = plt.subplots( 1, 2, figsize=(8,4) )
        axs = axs.ravel()
        axs[0].imshow( np.moveaxis( input[i], [0,1,2], [2,0,1] )[:,:,1:] )
        axs[1].imshow( np.moveaxis( output[i], [0,1,2], [2,0,1] )[:,:,1:] )
        plt.show()

def plot_loss(train_loss, val_loss):
    """
    Plot the validation and test losses over epochs.
    
    Parameters:
    -----------
    `val_losses` : list, the validation losses over epochs.
    `test_losses` : list, the test losses over epochs.
    """
    epochs = len(train_loss)
    print("Total epochs: ", epochs)

    plt.plot(range(epochs), train_loss, label='train')
    plt.plot(range(epochs), val_loss, label='validation')
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.title('Loss over Epochs')
    plt.legend()
    plt.show()

def generate_latent(model, dataloader, device):
    """
    Generate latent space vectors for all the images in the dataset

    Parameters:
    -----------
    model: VAE model
    dataloader: PyTorch dataloader
    device: torch.device

    Returns:
    --------
    mus: torch.Tensor containing the mu vectors for each image
    logvars: torch.Tensor containing the logvar vectors for each image       
    """
    mus = []
    logvars = []
    model.eval()  # Set the model to evaluation mode
    with torch.no_grad():  # No need to track gradients
        for data in dataloader:
            mu, logvar = model.encoder(data.to(device))  # Get mu and logvar
            mus.append(mu)
            logvars.append(logvar)
    mus = torch.cat(mus, dim=0)  # Concatenate all mu and logvar tensors
    logvars = torch.cat(logvars, dim=0)
    return mus, logvars

def check_distribution(mus, logvars):
    """
    Check that the distribution of the latent space vectors is close to a standard normal distribution

    Parameters:
    -----------
    mus: torch.Tensor containing the mu vectors for each image
    logvars: torch.Tensor containing the logvar vectors for each image
    """
    mus = mus.cpu().numpy()
    stds = np.sqrt(np.exp(logvars.cpu().numpy()))  # Calculate standard deviations from log variances

    mu_mean = np.mean(mus)
    mu_std = np.std(mus)

    std_mean = np.mean(stds)
    std_std = np.std(stds)

    print(f"Mu: mean={mu_mean}, std={mu_std}") # Check that the mean and std are close to 0 and 1 respectively
    print(f"Std: mean={std_mean}, std={std_std}") # Check that the mean and std are close to 0 and 1 respectively


def visualize_generated_images(generated_samples):
    """
    Visualize the generated samples.

    Parameters:
    -----------
    `generated_samples` : numpy array, the generated samples
    """
    num_samples = generated_samples.shape[0]
    fig, axs = plt.subplots(1, num_samples, figsize=(num_samples * 2, 2))

    for i in range(num_samples):
        axs[i].imshow(np.moveaxis(generated_samples[i], [0, 1, 2], [2, 0, 1]))
        axs[i].axis('off')

    plt.show()

def calculate_losses(model, test_loader, device, loss_function):
    """
    Calculate the reconstruction losses for all the images in the test set.
    
    Parameters:
    -----------
    `model` : VAE object, the trained VAE model
    `test_loader` : PyTorch dataloader, the test set
    `device` : torch.device, the device to use for predicting
    `loss_function` : function, the loss function to use for calculating the reconstruction loss
    
    Returns:
    --------    
    `reconstruction_losses` : list, the reconstruction losses for all the images in the test set
    """
    model.eval()
    reconstruction_losses = []
    originals = []
    reconstructions = []
    with torch.no_grad():
        for i, data in enumerate(test_loader):
            data = data.to(device)
            recon_batch, mu, logvar = model(data)
            recon_loss = loss_function(recon_batch, data, mu, logvar)
            reconstruction_losses.append(recon_loss.item())
            originals.append(data)
            reconstructions.append(recon_batch)

    reconstruction_losses = np.array(reconstruction_losses)
    sorted_indices = np.argsort(reconstruction_losses)
    best_5_indices = sorted_indices[:5]
    worst_5_indices = sorted_indices[-5:]

    originals = [img for batch in originals for img in batch]
    reconstructions = [img for batch in reconstructions for img in batch]

    return best_5_indices, worst_5_indices, originals, reconstructions

def plot_reconstructions(indices, originals, reconstructions, title):
    """
    Plot the original and reconstructed images for the given indices.
    
    Parameters:
    -----------
    `indices` : list, the indices of the images to plot
    `originals` : list, the original images
    `reconstructions` : list, the reconstructed images
    `title` : str, the title of the plot
    """
    fig, axes = plt.subplots(2, len(indices), figsize=(20, 8))
    for i, idx in enumerate(indices):
        axes[0, i].imshow(originals[idx].cpu().numpy()[:3].transpose(1, 2, 0))
        axes[0, i].set_title("Original")
        axes[1, i].imshow(reconstructions[idx].cpu().numpy()[:3].transpose(1, 2, 0))
        axes[1, i].set_title(title)

    plt.show()

def vae_loss_function(recon_x, x, mu, logvar):
    """
    VAE loss function which is the sum of a reconstruction term, and a 
    KL-divergence term.
    """
    # Reconstruction term
    MSE = torch.nn.functional.mse_loss(recon_x, x, reduction='sum')
    # KL divergence term
    KLD = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
    return MSE + KLD