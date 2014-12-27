#   Copyright 2015 Roy Portas
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.


from PIL import Image
from datetime import datetime
from PySide import QtGui
from os import listdir
from os.path import isfile, join, splitext
from threading import Thread
import sys
import requests
import webbrowser
import json

from gui import Ui_MainWindow as mainFrame

tags = {"Date taken": 36867, "GPS data": 34853}
api_key = "" # The api key for google's API
#TODO: Add social media feeds


class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        """Initialised the window"""
        global api_key
        super(MainWindow, self).__init__()
        self.ui = mainFrame()
        self.ui.setupUi(self)
        self.ui.actionLoad_Directory.triggered.connect(self.load_images)
        self.ui.actionAbout.triggered.connect(self.show_about)
        self.ui.plotButton.clicked.connect(self.get_selected)
        self.ui.analyseButton.clicked.connect(self.analyse_images)
        self.list_widget = self.ui.listWidget
        self.progress_bar = self.ui.progressBar

        # Load config file
        try:
            with open('keys.cfg', 'r') as f:
                raw = f.read()
                j = json.loads(raw)
                api_key = j['google-key']
        except IOError:
            print("Failed to open key file")
            self.ui.analyseButton.setEnabled(False)


        self.images = []
        self.file_types = ['.jpg', '.png']

        self.show()

    def show_about(self):
        QtGui.QMessageBox.about(self, "About EXIF Extractor",
                                """<p>Copyright (c) 2015 Roy Portas""")

    def open_directory(self):
        """Opens a directory to get the filenames of image files"""
        dir_name = QtGui.QFileDialog.getExistingDirectory(self, "Select Directory")
        return dir_name

    def get_selected(self):
        try:
            item = self.list_widget.currentRow()
            lat = self.images[item].location[0]
            lon = self.images[item].location[1]
            webbrowser.open_new_tab("http://maps.google.com/?q=loc:{},{}".format(lat, lon))
        except:
            # Catch in case user hits button without anything loaded
            pass

    def analyse_images(self):
        """Analyses GPS data to determine where the photos were taken"""
        threads = []
        for image in self.images:
            lat = image.location[0]
            lon = image.location[1]
            t = Thread(target=self.gps_lookup, args=(lat, lon, image))
            t.start()
            threads.append(t)

        if len(threads) != 0:

            stillAlive = 1
            aliveThreads = 0
            while stillAlive:
                aliveThreads = 0
                for thread in threads:
                    if thread.isAlive() == 1:
                        aliveThreads += 1
                prog = aliveThreads / len(threads) * 100
                self.progress_bar.setValue(prog)
                if aliveThreads == 0:
                    stillAlive = 0

        self.update_listbox()

    def gps_lookup(self, lat, lon, image):
        """Used to simplify the threading"""
        image.poi = lookup_location(lat, lon)

    def load_images(self):
        """Loads the images"""
        images = []
        dir_name = self.open_directory()
        if dir_name != '':
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

        self.update_listbox()

        # Update the image count
        self.ui.numOfPoints.setText(str(len(self.images)))

    def update_listbox(self):
        self.list_widget.clear()
        for image in self.images:
            self.list_widget.addItem(str(image))

class ImageData:
    def __init__(self, fname, date, location):
        self.fname = fname
        self.date = date
        self.location = location
        self.poi = None

    def __repr__(self):
        return "{} - {} - {}".format(self.fname, self.date, self.location)

    def __str__(self):
        if self.poi == None:
            return "{} - ({:.4f}, {:.4f})".format(self.date, self.location[0], self.location[1])
        else:
            return "{} -> {} - {} - ({:.4f}, {:.4f})".format(self.poi[0], self.poi[1], self.date,
                                                             self.location[0], self.location[1])


#TODO: Refine this function and implement
def lookup_location(lat, lon):
    """Looks up a location via Google Servers"""
    try:
        r = requests.get("https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={},{}&rankby=distance&types=establishment&key={}".\
            format(lat, lon, api_key))
        j = r.json()
        name = j['results'][0]['name'] # Should get closest result
        address = j['results'][0]['vicinity']

        location = [name, address]
        return location
    except requests.ConnectionError:
        pass



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