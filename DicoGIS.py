# -*- coding: UTF-8 -*-
#!/usr/bin/env python
from __future__ import unicode_literals
#-------------------------------------------------------------------------------
# Name:         DicoGIS
# Purpose:      Automatize the creation of a dictionnary of geographic data
#                   contained in a folders structures.
#                   It produces an Excel output file (.xls)
#
# Author:       Julien Moura (https://github.com/Guts/)
#
# Python:       2.7.x
# Created:      14/02/2013
# Updated:      31/08/2013
#
# Licence:      GPL 3
#-------------------------------------------------------------------------------

################################################################################
########### Libraries #############
###################################
# Standard library
from Tkinter import *     # GUI
from tkFileDialog import askdirectory, asksaveasfilename    # dialogs
from tkMessageBox import showinfo as info
from ttk import *       # advanced graphic widgets
import tkFont

from sys import exit, platform
from os import  listdir, walk, path         # files and folder managing
from os import environ as env
from time import strftime
from webbrowser import open_new
import threading    # handling various subprocess

import logging      # log files
from logging.handlers import RotatingFileHandler

# Python 3 backported
from collections import OrderedDict as OD   # ordered dictionary

# 3rd party libraries
from osgeo import ogr    # spatial files
from xlwt import Workbook, Font, XFStyle, easyxf, Formula  # excel writer
from xlwt import Alignment, Pattern, Borders, easyfont      # excel style config
from xml.etree import ElementTree as ET     # XML parsing and writer

# Custom modules
from modules import InfosOGR    # custom extractor for geographic data
from modules import InfosOGR_PG    # custom extractor for geographic data in PostGIS databases

# Imports depending on operating system
if platform == 'win32':
    u""" windows """
    from os import startfile                            # to open a folder/file

################################################################################
########### Variables #############
###################################

class DicoGIS(Tk):
    def __init__(self):
        u""" Main window constructor
        Creates 1 frame and 2 labelled subframes"""
        # creation and configuration of log file
        # see: http://sametmax.com/ecrire-des-logs-en-python/
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)  # all errors will be get
        log_form = logging.Formatter('%(asctime)s || %(levelname)s || %(message)s')
        logfile = RotatingFileHandler('DicoGIS.log', 'a', 5000000, 1)
        logfile.setLevel(logging.DEBUG)
        logfile.setFormatter(log_form)
        self.logger.addHandler(logfile)
        self.logger.info('\t ====== DicoGIS ======')  # first write

        # basics settings
        Tk.__init__(self)               # constructor of parent graphic class
        self.title(u'DicoGIS')
        self.style = Style().theme_use('clam')
        if platform == 'win32':
            self.logger.info('Operating system: Windows')
            self.iconbitmap('DicoGIS.ico')    # windows icon
            self.uzer = env.get(u'USERNAME')
        elif platform == 'linux2':
            self.logger.info('Operating system: Linux')
            self.uzer = env.get(u'USER')
            icon = Image("photo", file = r'img/DicoGIS_logo.gif')
            self.call('wm','iconphoto', self._w, icon)
        elif platform == 'darwin':
            self.logger.info('Operating system: Mac')
            self.uzer = env.get(u'USER')
        else:
            self.logger.warning('Operating system unknown')
        self.resizable(width = False, height = False)
        self.focus_force()

        # variables
        self.num_folders = 0
        self.def_rep = ""       # default folder to search for
        self.def_lang = 'FR'    # default language to start
        self.li_shp = []         # list for shapefiles path
        self.li_tab = []         # list for MapInfo tables path
        self.today = strftime("%Y-%m-%d")   # date of the day
        self.dico_layer = OD()    # dictionary where will be stored informations
        self.dico_fields = OD()    # dictionary for fields information
        self.dico_err = OD()     # errors list
        li_lang = [lg[5:-4] for lg in listdir(r'locale')] # available languages
        self.blabla = OD()      # texts dictionary

        # GUI fonts
        ft_tit = tkFont.Font(family="Times", size=10, weight=tkFont.BOLD)

        # fillfulling
        self.load_settings()
        self.load_texts(self.def_lang)

        # Frames
        self.FrPath = Labelframe(self, name ='files',
                                       text = self.blabla.get('gui_fr1'))
        self.FrDb = Labelframe(self, name ='database',
                                       text = self.blabla.get('gui_fr2'))
        self.FrProg = Labelframe(self, name ='progression',
                                       text = self.blabla.get('gui_prog'))

            ## Frame 1: path of geofiles
        # target folder
        self.labtarg = Label(self.FrPath, text = self.blabla.get('gui_path'))
        self.target = Entry(self.FrPath, width = 35)
        self.browsetarg = Button(self.FrPath,       # browse button
                                 text = self.blabla.get('gui_choix'),
                                 command = self.setpathtarg,
                                 takefocus = True)
        self.browsetarg.focus_force()               # force the focus on
        self.nameoutput = Label(self.FrPath,
                                 text = self.blabla.get('gui_fic'))
        self.output = Entry(self.FrPath, width = 35)
        # widgets placement
        self.labtarg.grid(row = 1, column = 1, columnspan = 1, sticky = N+S+W+E, padx = 2, pady = 2)
        self.target.grid(row = 1, column = 2, columnspan = 1, sticky = N+S+W+E, padx = 2, pady = 2)
        self.browsetarg.grid(row = 1, column = 3, sticky = N+S+W+E, padx = 2, pady = 2)
        self.nameoutput.grid(row = 3, column= 1, sticky = N+S+W+E, padx = 2, pady = 2)
        self.output.grid(row = 3, column= 2, columnspan = 2, sticky = N+S+W+E, padx = 2, pady = 2)


            ## Frame 2: Database
        # variables
        self.host = StringVar(self.FrDb, 'localhost')
        self.port = IntVar(self.FrDb, 5432)
        self.dbnb = StringVar(self.FrDb)
        self.user = StringVar(self.FrDb, 'postgres')
        self.pswd = StringVar(self.FrDb)
        # Form widgets
        self.ent_H = Entry(self.FrDb, textvariable = self.host)
        self.ent_P = Entry(self.FrDb, textvariable = self.port, width = 5)
        self.ent_D = Entry(self.FrDb, textvariable = self.dbnb)
        self.ent_U = Entry(self.FrDb, textvariable = self.user)
        self.ent_M = Entry(self.FrDb, textvariable = self.pswd, show='*')
        # Label widgets
        self.lb_H = Label(self.FrDb, text = self.blabla.get('gui_host'))
        self.lb_P = Label(self.FrDb, text = self.blabla.get('gui_port'))
        self.lb_D = Label(self.FrDb, text = self.blabla.get('gui_db'))
        self.lb_U = Label(self.FrDb, text = self.blabla.get('gui_user'))
        self.lb_M = Label(self.FrDb, text = self.blabla.get('gui_mdp'))
        # widgets placement
        self.ent_H.grid(row = 1, column = 1, columnspan = 2, sticky = N+S+E+W, padx = 2, pady = 2)
        self.ent_P.grid(row = 1, column = 3, columnspan = 1, sticky = N+S+E, padx = 2, pady = 2)
        self.ent_D.grid(row = 2, column = 1, columnspan = 1, sticky = N+S+E+W, padx = 2, pady = 2)
        self.ent_U.grid(row = 2, column = 3, columnspan = 1, sticky = N+S+E+W, padx = 2, pady = 2)
        self.ent_M.grid(row = 3, column = 1, columnspan = 3, sticky = N+S+E+W, padx = 2, pady = 2)
        self.lb_H.grid(row = 1, column = 0, sticky = N+S+E+W, padx = 2, pady = 2)
        self.lb_P.grid(row = 1, column = 3, sticky = N+S+W, padx = 2, pady = 2)
        self.lb_D.grid(row = 2, column = 0, sticky = N+S+W, padx = 2, pady = 2)
        self.lb_U.grid(row = 2, column = 2, sticky = N+S+W, padx = 2, pady = 2)
        self.lb_M.grid(row = 3, column = 0, sticky = N+S+W+E, padx = 2, pady = 2)

            ## Frame 3: Progression bar
        # variables
        self.status = StringVar(self.FrProg, '')
        # widgets
        self.prog_layers = Progressbar(self.FrProg,
                                       orient="horizontal")
        Label(self.FrProg, textvariable = self.status,
                           foreground = 'DodgerBlue').pack()
        # widgets placement
        self.prog_layers.pack(expand=1, fill='both')

            ## Main frame
        self.typo = IntVar(self, 1)    # type value (files or database)
        # Hola
        self.welcome = Label(self,
                             text = self.blabla.get('hi') + self.uzer,
                             font = ft_tit,
                             foreground = "red2")
        # Imagen
        self.icone = PhotoImage(file = r'img/DicoGIS_logo.gif')
        Label(self, borderwidth = 2,
                    image = self.icone).grid(row = 1,
                                             rowspan = 3,
                                             column = 0,
                                             padx = 2,
                                             pady = 2,
                                             sticky = W)
        # credits
        s = Style(self)
        s.configure('Kim.TButton', foreground='DodgerBlue', borderwidth = 0)
        Button(self, text = 'by Julien Moura\n      2013',
                     style = 'Kim.TButton',
                     command = lambda: open_new('https://github.com/Guts')).grid(row = 4,
                                                                                 padx = 2,
                                                                                 pady = 2,
                                                                                 sticky = W+E)
        # language switcher
        self.ddl_lang = Combobox(self, values = li_lang, width = 5)
        self.ddl_lang.current(li_lang.index(self.def_lang))
        self.ddl_lang.bind("<<ComboboxSelected>>", self.change_lang)
        # type switcher
        rd_file = Radiobutton(self, text = 'Fichiers', 
                                           variable = self.typo, 
                                           value = 1,
                                           command = self.change_type)
        rd_pg = Radiobutton(self, text = 'PostGIS', 
                                         variable = self.typo, 
                                         value = 2,
                                           command = self.change_type)
        # Basic buttons
        #img_proc = PhotoImage(master = self, file = 'img/Processing_TNP_10789.gif')
        self.val = Button(self, text = self.blabla.get('gui_go'),
                                state = ACTIVE,
                                command = self.process)
        #self.val.config(image = img_proc)
        self.can = Button(self, text = self.blabla.get('gui_quit'),
                           command = self.destroy)

        # widgets placement
        self.welcome.grid(row = 1, column = 1, columnspan = 1, sticky = N+S,
                          padx = 2, pady = 2)
        self.ddl_lang.grid(row=1, column = 1, sticky = N+S+E, padx = 2, pady = 2)
        rd_file.grid(row=2, column = 1, sticky = N+S+W, padx = 2, pady = 2)
        rd_pg.grid(row=2, column = 1, sticky = N+S+E, padx = 2, pady = 2)
        self.val.grid(row = 5, column = 1, columnspan = 2,
                            sticky = N+S+W+E, padx = 2, pady = 2)
        self.can.grid(row = 5, column = 0, sticky = N+S+W+E, padx = 2, pady = 2)
        # Frames placement
        self.FrProg.grid(row = 4, column = 1, sticky = N+S+W+E, padx = 2, pady = 2)
        rd_file.invoke()    # to provoc the type (frame 2) placement

    def load_settings(self):
        u""" load settings from last execution """
        # open xml cursor
        xml = ET.parse('settings.xml')
        # parsing
        for elem in xml.getroot().getiterator():
            if elem.tag == 'codelang':
                self.def_lang = elem.text
                continue
            elif elem.tag == 'rep_defaut':
                self.def_rep = elem.text
                continue
        # End of function
        return self.def_rep, self.def_lang


    def save_settings(self):
        u""" save last options in order to make the next excution more easy """
        # open xml cursor
        xml = ET.parse('settings.xml')
        # parsing
        for elem in xml.getroot().getiterator():
            if elem.tag == 'codelang':
                elem.text = self.ddl_lang.get()
                continue
            elif elem.tag == 'rep_defaut':
                elem.text = self.target.get()
                continue
        # Sauvegarde du fichier XML
        xml.write(r'settings.xml',
                  encoding = 'utf-8',
                  xml_declaration = 'version="1.0"',
                  method = 'xml')
        # End of function
        return self.def_rep, self.def_lang


    def change_lang(self, event):
        u""" update the texts dictionary with the language selected """
        new_lang = event.widget.get()
        self.logger.info('\tLanguage switched to: %s' %event.widget.get())
        # change to the new language selected
        self.load_texts(new_lang)
        # update widgets text
        self.welcome.config(text = self.blabla.get('hi') + self.uzer)
        self.can.config(text = self.blabla.get('gui_quit'))
        self.FrPath.config(text = self.blabla.get('gui_fr1'))
        self.FrDb.config(text = self.blabla.get('gui_fr2'))
        self.FrProg.config(text = self.blabla.get('gui_prog'))
        self.labtarg.config(text = self.blabla.get('gui_path'))
        self.browsetarg.config(text = self.blabla.get('gui_choix'))
        self.val.config(text = self.blabla.get('gui_go'))
        self.nameoutput.config(text = self.blabla.get('gui_fic'))
        self.lb_H.config(text = self.blabla.get('gui_host'))
        self.lb_P.config(text = self.blabla.get('gui_port'))
        self.lb_D.config(text = self.blabla.get('gui_db'))
        self.lb_U.config(text = self.blabla.get('gui_user'))
        self.lb_M.config(text = self.blabla.get('gui_mdp'))

        # End of function
        return self.blabla


    def load_texts(self, lang='FR'):
        u""" Load texts according to the selected language """
        # clearing the text dictionary
        self.blabla.clear()
        # open xml cursor
        xml = ET.parse('locale/lang_' + lang + '.xml')
        # Looping and gathering texts from the xml file
        for elem in xml.getroot().getiterator():
            self.blabla[elem.tag] = elem.text
        # updating the GUI
        self.update()
        # Fin de fonction
        return self.blabla


    def change_type(self):
        u""" switch between the available types of data (files or database) """
        if self.typo.get() == 1:
            self.logger.info('Type switched to: files structure')
            self.FrDb.grid_forget()
            self.status.set('')
            self.FrPath.grid(row = 3, column = 1, sticky = N+S+W+E, padx = 2, pady = 2)
        elif self.typo.get() == 2:
            self.logger.info('Type switched to: database')
            self.FrPath.grid_forget()
            self.status.set('')
            self.FrDb.grid(row = 3, column = 1, sticky = N+S+W+E, padx = 2, pady = 2)
        # End of function
        return self.typo



    def setpathtarg(self):
        """ ...browse and insert the path of target folder """
        foldername = askdirectory(parent = self,
                                  initialdir = self.def_rep,
                                  mustexist = True,
                                  title = self.blabla.get('gui_cible'))
        # check if a folder has been choosen
        if foldername:
            try:
                self.target.delete(0, END)
                self.target.insert(0, foldername)
            except:
                info(title = self.blabla.get('nofolder'),
                     message = self.blabla.get('nofolder'))
                return
        # set the default output file
        self.output.delete(0, END)
        self.output.insert(0, "DicoShapes_" + path.split(self.target.get())[1]
                            + "_" + self.today + ".xls"  )
        # calculate number of shapefiles and MapInfo files in a separated thread

        proc = threading.Thread(target = self.ligeofiles, args = (foldername, ))
        proc.daemon = True
        proc.start()
        # end of function
        return foldername


    def ligeofiles(self, foldertarget):
        u""" List shapefiles and MapInfo files (.tab, not .mid/mif) contained
        in the folders structure """
        # reseting global variables
        self.li_shp = []
        self.li_tab = []
        self.browsetarg.config(state = DISABLED)
        # Looping in folders structure
        self.status.set(self.blabla.get('gui_prog1'))
        self.prog_layers.start()
        self.logger.info('Begin of folders parsing')
        for root, dirs, files in walk(foldertarget):
            self.num_folders = self.num_folders + len(dirs)
            for i in files:
                # Looping on files contained
                if path.splitext(path.join(root, i))[1] == u'.shp' and \
                   path.isfile(path.join(root, i)[:-4] + u'.dbf') and \
                   path.isfile(path.join(root, i)[:-4] + u'.shx') and \
                   path.isfile(path.join(root, i)[:-4] + u'.prj'):
                    # add complete path of shapefile
                    self.li_shp.append(path.join(root, i))
                elif path.splitext(path.join(root, i))[1] == u'.tab' and \
                   path.isfile(path.join(root, i)[:-4] + u'.dat') and \
                   path.isfile(path.join(root, i)[:-4] + u'.map') and \
                   path.isfile(path.join(root, i)[:-4] + u'.id'):
                    # add complete path of MapInfo file
                    self.li_tab.append(path.join(root, i))
        self.prog_layers.stop()
        self.logger.info('End of folders parsing: %s folders explored', str(self.num_folders))
        # Lists ordering and tupling
        self.li_shp.sort()
        self.li_shp = tuple(self.li_shp)
        self.li_tab.sort()
        self.li_tab = tuple(self.li_tab)
        # setting the label text and activing the buttons
        self.status.set(unicode(len(self.li_shp)) + u' shapefiles - '
                        + unicode(len(self.li_tab)) + u' tables (MapInfo) - '
                        + unicode(self.num_folders) + self.blabla.get('log_numfold'))
        self.browsetarg.config(state = ACTIVE)
        self.val.config(state = ACTIVE)
        # End of function
        return foldertarget, self.li_shp, self.li_tab

    def process(self):
        print 'process initialized'
        if self.typo.get() == 1:
            self.logger.info('=> files process started')
            self.process_files()
        elif self.typo.get() == 2:
            self.logger.info('=> DB process started')
            self.process_db()
        return

    def process_files(self):
        u""" launch the different processes """
        # check if there are some layers into the folder structure
        if len(self.li_shp) + len(self.li_tab) == 0:
            erreurStop(self.blabla.get('nodata'))
            return
        # creating the Excel workbook
        self.configexcel()
        self.logger.info('Excel file created')
        # configuring the progression bar
        self.prog_layers["maximum"] = len(self.li_shp) + len(self.li_tab)
        self.prog_layers["value"]
        # getting the info from shapefiles and compile it in the excel
        line = 1    # line of dictionary
        self.logger.info('\tShapefiles processed')
        for shp in self.li_shp:
            """ looping on shapefiles list """
            self.status.set(path.basename(shp))
            self.logger.info('\n' + shp)
            # reset recipient data
            self.dico_layer.clear()
            self.dico_fields.clear()
            # creating separated process threads
            InfosOGR(shp, self.dico_layer, self.dico_fields, 'shape', self.blabla)
            self.logger.info('\t Infos OK')
            # getting the informations
            # writing to the Excel dictionary
            self.dictionarize(self.dico_layer, self.dico_fields, self.feuy1, line)
            self.logger.info('\t Wrote into the dictionary')
            # increment the line number
            line = line +1
            # increment the progress bar
            self.prog_layers["value"] = self.prog_layers["value"] +1
            self.update()
        # getting the info from mapinfo tables and compile it in the excel
        self.logger.info('\n\tMapInfo tables processed')
        for tab in self.li_tab:
            """ looping on MapInfo tables list """
            self.status.set(path.basename(tab))
            self.logger.info('\n' + tab)
            # reset recipient data
            self.dico_layer.clear()
            self.dico_fields.clear()
            # getting the informations
            InfosOGR(tab, self.dico_layer, self.dico_fields, 'table', self.blabla)
            self.logger.info('\t Infos OK')
            # writing to the Excel dictionary
            self.dictionarize(self.dico_layer, self.dico_fields, self.feuy1, line)
            self.logger.info('\t Wrote into the dictionary')
            # increment the line number
            line = line +1
            # increment the progress bar
            self.prog_layers["value"] = self.prog_layers["value"] +1
            self.update()
        # saving dictionary
        self.savedico()
        self.logger.info('\n\tWorkbook saved: %s', self.output.get())
        # saving settings
        self.save_settings()

        # quit and exit
        if platform == 'win32':
            startfile(self.output.get())
        self.destroy()
        exit()

        # End of function
        return

    def process_db(self):
        u""" launch the different processes """
        # creating the Excel workbook
        self.configexcel()
        self.logger.info('Excel file created')
        # # configuring the progression bar
        # self.prog_layers["maximum"] = len(self.li_shp) + len(self.li_tab)
        # self.prog_layers["value"]
        # getting the info from shapefiles and compile it in the excel
        line = 1    # line of dictionary
        self.logger.info('\tPostGIS table processing...')
        try:
            conn = ogr.Open("PG: host=%s port=%s dbname=%s user=%s password=%s" %(self.host.get(),
                                                                                  self.port.get(),
                                                                                  self.dbnb.get(), 
                                                                                  self.user.get(), 
                                                                                  self.pswd.get()))
        except:
            self.logger.info('Connection to database failed. Check your connection settings.')
            exit()
        # parsing the layers
        for layer in conn:
            InfosOGR_PG(layer, self.dico_layer, self.dico_fields, 'pg', self.blabla)
            self.logger.info('Table examined: %s' % layer.GetName())
            # writing to the Excel dictionary
            self.dictionarize(self.dico_layer, self.dico_fields, self.feuy1, line)
            self.logger.info('\t Wrote into the dictionary')
            # increment the line number
            line = line +1
            # increment the progress bar
            #self.prog_layers["value"] = self.prog_layers["value"] +1
            self.update()
        # saving dictionary
        self.savedico()
        self.logger.info('\n\tWorkbook saved: %s', self.output.get())
        # saving settings
        self.save_settings()

        # quit and exit
        if platform == 'win32':
            startfile(self.output.get())
        self.destroy()
        exit()

        # End of function
        return

    def check_fields(self):
        u""" Check if fields are not empty """
        # error message
        msj = u'Any fields should be empty'
        # checking empty fields
        if self.host.get() == u'':
            self.H.configure(background = 'red')
        if self.port.get() == 0:
            self.P.configure(background = 'red')
        if self.dbnb.get() == u'':
            self.D.configure(background = 'red')
        if self.user.get() == u'':
            self.U.configure(background = 'red')
        if self.pswd.get() == u'':
            self.M.configure(background = 'red')

        # Acción según si hay error(es) o no
        if err != 0:
            showerror(title = u'Error: campo(s) vacío(s)',
                      message = msj)
        # End of function
        return err

    def testconnexion(self):
        u""" testing database connection settings """
        try:
            conn = ogr.Open(host = self.host.get(), dbname = self.dbnb.get(),
                            port = self.port.get(), user = self.user.get(),
                            password = self.pswd.get())
            curs = conn.cursor()
            # check PostgreSQL and PostGIS versions
            try:
                curs.execute('SELECT version()')
                ver = curs.fetchone()
                self.logger.info('Connection successed: connecting people!')
                self.logger.info('Database version: %s' %ver)
            except DatabaseError, e:
                showerror(title = u'Connection issue',
                message = 'Connection aborted. Error:\n' + str(e))
                return
            # change the confirmation button
            self.val.config(text = '¡D A L E!')
            showinfo(title = u'Connection successed',
                     message = u'Test of connection settings successed')
            self.ok = 1

        except pg.OperationalError, e:
            showerror(title = u'Connection issue',
                      message = 'Connection aborted. Error:\n' + str(e))
            return

        except ImportError , e:
            return None


    def configexcel(self):
        u""" create and configure the Excel workbook """
        # Basic configurationdu
        self.book = Workbook(encoding = 'utf8')
        self.feuy1 = self.book.add_sheet(u'DicoGIS', cell_overwrite_ok=True)

        # Some customization: fonts and styles
        # first line style
        self.entete = easyxf()
            # font
        font1 = Font()
        font1.name = 'Times New Roman'
        font1.bold = True
            # alignment
        alig1 = Alignment()
        alig1.horz = 2
            # assign
        self.entete.font = font1
        self.entete.alignment = alig1

        # hyperlinks style
        self.url = easyxf(u'font: underline single')
        # errors style
        self.erreur = easyxf('pattern: pattern solid;'
                             'font: colour red, bold True;')

        # columns name
        self.feuy1.write(0, 0, self.blabla.get('nomfic'), self.entete)
        self.feuy1.write(0, 1, self.blabla.get('path'), self.entete)
        self.feuy1.write(0, 2, self.blabla.get('theme'), self.entete)
        self.feuy1.write(0, 3, self.blabla.get('num_attrib'), self.entete)
        self.feuy1.write(0, 4, self.blabla.get('num_objets'), self.entete)
        self.feuy1.write(0, 5, self.blabla.get('geometrie'), self.entete)
        self.feuy1.write(0, 6, self.blabla.get('srs'), self.entete)
        self.feuy1.write(0, 7, self.blabla.get('srs_type'), self.entete)
        self.feuy1.write(0, 8, self.blabla.get('codepsg'), self.entete)
        self.feuy1.write(0, 9, self.blabla.get('emprise'), self.entete)
        self.feuy1.write(0, 10, self.blabla.get('date_crea'), self.entete)
        self.feuy1.write(0, 11, self.blabla.get('date_actu'), self.entete)
        self.feuy1.write(0, 12, self.blabla.get('format'), self.entete)
        self.feuy1.write(0, 13, self.blabla.get('li_chps'), self.entete)

        # end of function
        return self.book, self.feuy1, self.entete, self.url, self.erreur

    def dictionarize(self, layer_infos, fields_info, sheet, line):
        u""" write the infos of the layer into the Excel workbook """
        # local variables
        champs = ""
        theme = ""

        # in case of a source error
        if layer_infos.get('error'):
            self.logger.warning('\tproblem detected')
            sheet.write(line, 0, layer_infos.get('name'))
            link = 'HYPERLINK("' + layer_infos.get(u'folder') \
                             + '"; "' + self.blabla.get('browse') + '")'
            sheet.write(line, 1, Formula(link), self.url)
            sheet.write(line, 2, self.blabla.get((layer_infos.get('error')), self.erreur))
            # Interruption of function
            return self.book, self.feuy1

        # Name
        sheet.write(line, 0, layer_infos.get('name'))
        # Path of containing folder formatted to be a hyperlink
        link = 'HYPERLINK("' + layer_infos.get(u'folder') \
                             + '"; "' + self.blabla.get('browse') + '")'
        sheet.write(line, 1, Formula(link), self.url)
        # Name of containing folder
        # with a specific exception to adapt to PACIVUR database
        if path.basename(layer_infos.get(u'folder')) != 'shp':
            sheet.write(line, 2, path.basename(layer_infos.get(u'folder')))
        else:
            sheet.write(line, 2, path.basename(path.dirname(layer_infos.get(u'folder'))))

        # Geometry type
        sheet.write(line, 5, layer_infos.get(u'type_geom'))
        # Spatial extent
        emprise = u"Xmin : " + unicode(layer_infos.get(u'Xmin')) +\
                  u", Xmax : " + unicode(layer_infos.get(u'Xmax')) +\
                  u", Ymin : " + unicode(layer_infos.get(u'Ymin')) +\
                  u", Ymax : " + unicode(layer_infos.get(u'Ymax'))
        sheet.write(line, 9, emprise)
        # Name of srs
        sheet.write(line, 6, layer_infos.get(u'srs'))
        # Type of SRS
        sheet.write(line, 7, layer_infos.get(u'srs_type'))
        # EPSG code
        sheet.write(line, 8, layer_infos.get(u'EPSG'))
        # Number of fields
        sheet.write(line, 3, layer_infos.get(u'num_fields'))
        # Name of objects
        sheet.write(line, 4, layer_infos.get(u'num_obj'))
        # Creation date
        sheet.write(line, 10, layer_infos.get(u'date_crea'))
        # Last update date
        sheet.write(line, 11, layer_infos.get(u'date_actu'))
        # Format of data
        sheet.write(line, 12, layer_infos.get(u'type'))
        # Field informations
        for chp in fields_info.keys():
            # field type
            if fields_info[chp][0] == 'Integer':
                tipo = self.blabla.get(u'entier')
            elif fields_info[chp][0] == 'Real':
                tipo = self.blabla.get(u'reel')
            elif fields_info[chp][0] == 'String':
                tipo = self.blabla.get(u'string')
            elif fields_info[chp][0] == 'Date':
                tipo = self.blabla.get(u'date')
            # concatenation of field informations
            try:
                champs = champs + chp +\
                         u" (" + tipo + self.blabla.get(u'longueur') +\
                         unicode(fields_info[chp][1]) +\
                         self.blabla.get(u'precision') +\
                         unicode(fields_info[chp][2]) + u") ; "
            except UnicodeDecodeError:
                # write a notification into the log file
                self.dico_err[layer_infos.get('name')] = self.blabla.get(u'err_encod') + \
                                                         chp.decode('latin1') + \
                                                         u"\n\n"
                # decode the fucking field name
                champs = champs +\
                         chp.decode('utf8') +\
                         u" (" + tipo +\
                         u", Lg. = " + unicode(fields_info[chp][1]) +\
                         u", Pr. = " + unicode(fields_info[chp][2]) + ") ; "
                # then continue
                continue

        # Once all fieds explored, write them
        sheet.write(line, 13, champs)

        # End of function
        return self.book, self.feuy1

    def savedico(self):
        u""" Save the Excel file """
        # Prompt of folder where save the file
        saved = asksaveasfilename(initialdir= self.target.get(),
                            defaultextension = '.xls',
                            initialfile = self.output.get(),
                            filetypes = [(self.blabla.get('gui_excel'),"*.xls")])

        # check if the extension is correctly indicated
        if path.splitext(saved)[1] != ".xls":
            saved = saved + ".xls"
        # save
        self.book.save(saved)
        self.output.delete(0, END)
        self.output.insert(0, saved)
        # notification
        total_files = unicode(len(self.li_shp) + len(self.li_tab))
        info(title=self.blabla.get('info_end'),
             message = self.blabla.get('info_end2'))

        # End of function
        return self.book, saved

    def erreurStop(self, mess):
        u""" In case of error, close the GUI and stop the program """
        info(title = u'Erreur', message = mess)
        self.logger.error(mess)
        self.root.destroy()
        exit()

################################################################################
###### Stand alone program ########
###################################

if __name__ == '__main__':
    app = DicoGIS()
    app.mainloop()


################################################################################
######## Former codelines #########
###################################