__author__ = 'Roy Portas'
__copyright__ = 'Copyright 2014'
__credits__ = ['Roy Portas']
__license__ = 'Apache 2.0'
__date__ = '23/12/2014'
__version__ = '1.0'
__email__ = 'royportas@gmail.com'

from PIL import Image
from datetime import datetime
from PySide import QtGui
from os import listdir
from os.path import isfile, join, splitext
import sys

from gui import Ui_MainWindow as mainFrame

tags = {"Date taken": 36867, "GPS data": 34853}

class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        """Initialised the window"""
        super(MainWindow, self).__init__()
        self.ui = mainFrame()
        self.ui.setupUi(self)
        self.ui.actionLoad_Directory.triggered.connect(self.load_images)
        self.ui.plotButton.clicked.connect(self.get_selected)
        self.list_widget = self.ui.listWidget

        self.images = []
        self.file_types = ['.jpg', '.png']

        self.show()

    def open_directory(self):
        """Opens a directory to get the filenames of image files"""
        dir_name = QtGui.QFileDialog.getExistingDirectory(self, "Select Directory")
        return dir_name

    def get_selected(self):
        item = self.list_widget.currentRow()
        print(self.images[item])

    def load_images(self):
        """Loads the images"""
        images = []
        dir_name = self.open_directory()
        dir_contents = listdir(dir_name)
        for item in dir_contents:
            path = join(dir_name, item)
            if isfile(path):
                ext = splitext(item)[-1].lower()
                if ext in self.file_types:
                    exif = get_exif(path, item)
                    if exif:
                        images.append(exif)

        # Sort the images by date
        self.images = []
        for image in images:
            inserted = 0
            if len(self.images) == 0:
                self.images.append(image)
            else:
                inserted = 0
                for ind in range(0, len(self.images)):
                    if image.date < self.images[ind].date:
                        if inserted == 0:
                            self.images.insert(ind, image)
                            inserted = 1
                if inserted == 0:
                    self.images.append(image)




        for image in self.images:
            self.list_widget.addItem(str(image))


class ImageData:
    def __init__(self, fname, date, location):
        self.fname = fname
        self.date = date
        self.location = location

    def __repr__(self):
        return "{} - {} - {}".format(self.fname, self.date, self.location)

    def __str__(self):
        return "{} - {}".format(self.date, self.location)


def get_exif(filename, name):
    """Gets exif data from a image"""
    img = Image.open(filename)

    try:
        if '_getexif' in dir(img):
            data = img._getexif()
            gps_data = data[tags["GPS data"]]


            # Handle the GPS data and do the conversion to decimal
            latitude = float(gps_data[2][0][0]) / float(gps_data[2][0][1]) + (float(gps_data[2][1][0]) / float(gps_data[2][1][1]))/60 + (float(gps_data[2][2][0]) / float(gps_data[2][2][1]))/3600
            if gps_data[1] == "S":
                latitude = -latitude

            longitude = float(gps_data[4][0][0]) / float(gps_data[4][0][1]) + (float(gps_data[4][1][0]) / float(gps_data[4][1][1]))/60 + (float(gps_data[4][2][0]) / float(gps_data[4][2][1]))/3600
            if gps_data[3] == "W":
                longitude = -longitude

            altitude = float(gps_data[6][0]) / float(gps_data[6][1])
            location = (latitude, longitude, altitude)

            date_str = data[tags['Date taken']]
            date = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")

            #Create the ImageData object
            img_data = ImageData(name, date, location)
            return img_data

        else:
            return None
    except:
        return None

def main():
    app = QtGui.QApplication(sys.argv)
    win = MainWindow()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()