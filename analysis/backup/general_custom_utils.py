# general_custom_utils.py
import os
import imageio
import time

def progressBar(iterable, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
    """
    Call in a loop to create terminal progress bar 
    https://stackoverflow.com/questions/3173320/text-progress-bar-in-terminal-with-block-characters
    @params:
        iterable    - Required  : iterable object (Iterable)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
         decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    total = len(iterable)
    # Progress Bar Printing Function
    def printProgressBar (iteration):
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        filledLength = int(length * iteration // total)
        bar = fill * filledLength + '▁' * (length - filledLength)
        print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
    # Initial Call
    #time.sleep(0.5)  # Pause so that eventual printout can be printed before the bar is initialized
    printProgressBar(0)
    # Update Progress Bar
    for i, item in enumerate(iterable):
        yield item
        printProgressBar(i + 1)
    # Print New Line on Complete
    print()
    

def create_output_folder(folder_path="default_subfolder"):
    if folder_path[-1:] != "/":
        folder_path= folder_path+"/"
    if not os.path.exists( folder_path ):
        #print("Saving output in", folder_path )
        os.makedirs( folder_path )
        

def images_to_gif(image_files, gif_path, duration=0.5):
    images = [imageio.imread(image_file) for image_file in image_files]

    # Save the images as an animated GIF
    imageio.mimsave(gif_path, images, format='GIF', duration=duration)
    print("created gif in "+gif_path)
