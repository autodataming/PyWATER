
"""
Run it by following command:
Install in pymol by following the path: Plugins -> Manage Plugins -> install
Restart the PyMol

Script to find important or conserved waters in protein structure (pdb).
Important or conserved waters are the waters molecules which are present in most or all available pdb structures when superimposed.

Copyright 2013 Hitesh Patel and B. Gruening

"""

import os
import urllib
import shutil
import re
import tempfile
import scipy.cluster.hierarchy as hcluster
from xml.dom.minidom import parseString
import numpy as np
from Tkinter import *
import tkMessageBox
import pymol.cmd as cmd
import logging

"""
    TODO:
    - To make running in Windows and Mac
    - Write a log file with enough outputs..
"""

# setup logging
logger = logging.getLogger('PyCWMs')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('pycwm.log')
fh.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)

def __init__(self):
    self.menuBar.addmenuitem('Plugin', 'command',
                        'Find Conserved Waters',
                        label = 'PyCWMs',
                        command = main)


def pdb_id_help():
    tkMessageBox.showinfo(title = 'PDB Identifier', 
        message = "The PDB id of the protein for which you like to find conserved waters.")

def chain_help():
    tkMessageBox.showinfo(title = 'Chain Identifier', 
        message = "The chain identifier of the protein for which you like to find conserved waters in above mentioned PDB.")

def seq_id_help():
    tkMessageBox.showinfo(title = 'Sequence identity cutoff', 
        message = """All the protein structures, clustered by BlastClust, having sequence identity more than given cutoff will be superimposed to find the conserved water molecules in query protein chain.
Minimum suggested Sequence identity cutoff is 95.""")

def resolution_help():
    tkMessageBox.showinfo(title = 'Structure resolution cutoff', 
        message = """All the protein structures to be superimposed will be filtered first according to the structure resolution cutoff. Only structures with better resolution than given cutoff will be used further.
Maximum suggested structure resolution cutoff is 2.5 A.""")

def refinement_quality_help():
    tkMessageBox.showinfo(title = 'Filter by refinement quality', message = "Choose either Mobility or Normalized B-factor as criteria to assess the refinement quality of crystal structure. Program will filter out the water molecules with bad refinement quality.")

def cluster_diameter_help():
    tkMessageBox.showinfo(title = 'Cluster diameter', 
        message = """Only water molecules closer than given cutoff will be put in one cluster. The less cluster diameter ensures each water molecule in a cluster from different structures.
Maximum suggested structure resolution cutoff is 2.0 A.""")

def prob_help():
    tkMessageBox.showinfo(title = 'Probability cutoff', 
        message = """Water molecules will be considered CONSERVED if their probability of being conserved is above given cutoff.
Value ranges from 0 to 1.
Minimum suggested value is 0.5
""")

def displayInputs(selectedStruturePDB, selectedStrutureChain, seq_id, resolution, cluster_diameter, prob):
    logger.info( 'Input values')
    logger.info( 'PDB id : ' + selectedStruturePDB)
    logger.info( 'Chain id : %s' % selectedStrutureChain)
    logger.info( 'Seqence identity cutoff : %s' % seq_id)
    logger.info( 'Structure resolution cutoff : %s' % resolution)
    logger.info( 'Cluster diameter : %s' % cluster_diameter)
    logger.info( 'probability cutoff : %s' % prob)


def displayInPyMOL(outdir, selectedPDBChain):
    pdbCWMs = os.path.join(outdir, '%s_withConservedWaters.pdb' % selectedPDBChain)
    pdb = os.path.join(outdir, '%s.pdb' % selectedPDBChain)

    queryProteinCWMs = '%s_withConservedWaters' % selectedPDBChai

    cmd.load(pdbCWMs)
    cmd.orient(queryProteinCWMs)
    cmd.h_add(queryProteinCWMs)

    cmd.select('cwm_protein','polymer and %s' % queryProteinCWMs)
    cmd.select('cwm_waters','resn hoh and %s' % queryProteinCWMs)
    cmd.select('cwm_ligand','organic and %s' % queryProteinCWMs)

    # h bonds between protein and waters
    cmd.select('don', '(elem n,o and (neighbor hydro)) and %s' % queryProteinCWMs)
    cmd.select('acc', '(elem o or (elem n and not (neighbor hydro))) and %s' % queryProteinCWMs)
    cmd.distance ('PW_HBA', '(cwm_protein and acc)','(cwm_waters and don)', 3.2)
    cmd.distance ('PW_HBD', '(cwm_protein and don)','(cwm_waters and acc)', 3.2)

    cmd.distance ('LW_HBA', '(cwm_ligand and acc)','(cwm_waters and don)', 3.2)
    cmd.distance ('LW_HBD', '(cwm_ligand and don)','(cwm_waters and acc)', 3.2)

    cmd.delete('don')
    cmd.delete('acc')

    cmd.set('dash_color','yellow')
    cmd.set('dash_gap',0.3)
    cmd.set('dash_length',0.2)
    cmd.set('dash_round_ends','on')
    cmd.set('dash_width',3)

    # color and display
    cmd.util.cbam('cwm_ligand')
    cmd.show_as('sticks','cwm_ligand')

    cmd.spectrum('b', 'blue_red', 'cwm_waters')
    cmd.set('sphere_scale',0.30,'cwm_waters')
    cmd.show_as('spheres','cwm_waters')

    cmd.hide('labels','*_HB*')
    cmd.remove('(hydro) and %s' % queryProteinCWMs)

    cmd.util.cbac('cwm_protein')
    cmd.set('transparency', 0.2)
    cmd.show('surface', 'cwm_protein')

    cmd.load(pdb)
    cmd.create('all waters', 'resn hoh and %s' % selectedPDBChain)
    cmd.color('red','ss h and %s' % selectedPDBChain)
    cmd.color('yellow','ss s and %s' % selectedPDBChain)
    cmd.color('green','ss l+ and %s' % selectedPDBChain)
    cmd.show_as('cartoon', selectedPDBChain)
    cmd.set('ray_shadows', 0)



def okMobility(pdbFile, mobilityCutoff=2.0):
    normBfactors = []
    OccupancyAndBfactor = []
    for line in open(pdbFile):
        line = line.strip()
        if line.startswith('HETATM'):
            OccupancyAndBfactor.append([float(line[54:60]),float(line[60:66])])
    occupancy = [a[0] for a in OccupancyAndBfactor]
    Bfactors = [a[1] for a in OccupancyAndBfactor]
    avgB = np.mean(Bfactors)
    avgO = np.mean(occupancy)
    for a in OccupancyAndBfactor:
        a.append((a[1]/avgB)/(a[0]/avgO))
    mobility = [a[2] for a in OccupancyAndBfactor]
    count = 0
    for a in mobility:
        if a >= mobilityCutoff:
            count+=1
    if count > 0:
        considerPDB = False
    else:
        considerPDB = True
    logging.info( '%s is considered : %s ' % (pdbFile, considerPDB))
    return considerPDB


def okBfactor(pdbFile,normBCutoff=1.0):
    occupancy = []
    Bfactors = []
    normBfactors = []
    for line in open(pdbFile):
        line = line.strip()
        if line.startswith('HETATM'):
            occupancy.append(float(line[54:60]))
            Bfactors.append(float(line[60:66]))
    avg = np.mean(Bfactors)
    stddev = np.sqrt(np.var(Bfactors))
    for b in Bfactors:
        normBfactors.append((b-avg)/stddev)
    count = 0
    for b in normBfactors:
        if b > normBCutoff:
            count+=1
    if count > (len(normBfactors)/5):
        considerPDB = False
    else:
        considerPDB = True
    return considerPDB


class Protein():
    def __init__(self, pdb_id, chain=False):
        self.pdb_id = pdb_id.lower()
        self.chain = chain.lower()
        self.pdb_id_folder = self.pdb_id[1:3]
        self.pdb_filename = self.pdb_id + '.pdb'
        self.water_coordinates = list()
        self.water_ids = list()
        self.waterIDCoordinates = {}

    def __repr__(self):
        return "%s_%s" % (self.pdb_id, self.chain)

    def calculate_water_coordinates(self, tmp_dir = False):
        path = os.path.join( tmp_dir, 'cwm_%s_Water.pdb' % self.__repr__() )
        logging.info( 'making water coordinates dictcionary...' )
        i = 1
        for line in open(path):
            line = line.strip()
            if line.startswith('HETATM'):
                key = self.__repr__()+'_'+str(i)
                self.waterIDCoordinates[key] = [line[30:38],line[38:46],line[46:54]]
                self.water_coordinates.append([line[30:38],line[38:46],line[46:54]])
                self.water_ids.append( key )
                i += 1
        return self.waterIDCoordinates


class ProteinsList():
    def __init__(self, ProteinName):
        self.ProteinName = ProteinName
        self.proteins = list()
        self.selectedPDBChain = ''
        self.probability = 0.7
        self.cluster_diameter = 1.5
        self.refinement = ''

    def add_protein(self, protein):
        self.proteins.add(protein)

    def add_protein_from_string(self, s):
        """
            accepts a '1234:B' formatted string and creates a protein object out of it
            if no double point is found, it is assumed that the whole string is the pdb id
        """
        s = s.strip()
        if s.find(':') > -1:
            pdb_id, chain = s.split(':')
        else:
            pdb_id = s
            chain = False
        assert len(pdb_id) == 4, '%s is not of length 4' % pdb_id
        p = Protein(pdb_id, chain)
        self.proteins.append(p)

    def pop(self, index):
        return self.proteins.pop(index)

    def remove(self, protein):
        return self.proteins.remove(protein)

    def __iter__(self):
        for protein in self.proteins:
            yield protein

    def __len__(self):
        return len(self.proteins)

    def __getitem__( self, key ) :
        if isinstance( key, slice ) :
            # Get the start, stop, and step from the slice
            return [self.proteins[ii] for ii in xrange(*key.indices(len(self)))]
        elif isinstance( key, int ):
            # Handle negative indices
            if key < 0 :
                key += len( self.proteins )
            if key >= len( self.proteins ) :
                raise IndexError, "The index (%d) is out of range." % key
            return self.proteins[key] #Get the data from elsewhere
        else:
            raise TypeError, "Invalid argument type."


def makePDBwithConservedWaters(ProteinsList, temp_dir, outdir):
    logging.debug( 'prob is ... %s' % ProteinsList.probability )
    cmd.delete('cwm_*')
    logging.info( 'loading all pdb chains ...' )
    for protein in ProteinsList:
        cmd.load(os.path.join(temp_dir, protein.pdb_filename),'cwm_%s' % protein.pdb_id)
        cmd.create('cwm_%s' % protein, 'cwm_%s & chain %s' % (protein.pdb_id, protein.chain))
        cmd.delete( 'cwm_%s' % protein.pdb_id )

    logging.info( 'Superimposing all pdb chains ...' )
    for protein in ProteinsList[1:]:
        cmd.super('cwm_%s' % protein, 'cwm_%s' % ProteinsList[0]) # cmd.super(str(protein)+'////CA', str(ProteinsList[0])+'////CA')
        cmd.orient( 'cwm_%s' % ProteinsList[0] )

    logging.info( 'Creating new pymol objects of only water molecules for each pdb chains ...' )
    for protein in ProteinsList:
        cmd.create('cwm_%s_Water' % protein, 'cwm_%s & resname hoh' % protein)

    logging.info( 'saving water molecules and proteins in separate pdb files for each pdb chains...' )
    for protein in ProteinsList:
        cmd.save(os.path.join(temp_dir, 'cwm_%s.pdb' % protein), 'cwm_%s' % protein)
        cmd.save(os.path.join(temp_dir, 'cwm_%s_Water.pdb' % protein), 'cwm_%s_Water' % protein)

    cmd.delete('cwm_*')

    ### filter ProteinsList by mobility or normalized B factor cutoff

    logging.debug( '1. filtered ProteinsList.proteins is %i proteins long :' % len(ProteinsList.proteins) )
    length = len(ProteinsList.proteins)
    if ProteinsList.refinement == 'Mobility':
        logging.info( 'Filter by Mobility' )
        for protein in reversed(ProteinsList.proteins):
            if not okMobility(os.path.join(temp_dir, 'cwm_%s_Water.pdb' % protein)):
                ProteinsList.proteins.remove(protein)

    if ProteinsList.refinement == 'Normalized B-factors': 
        logging.info( 'Filtering by Bfactors' )
        for protein in reversed(ProteinsList.proteins):
            if not okBfactor(os.path.join(temp_dir, 'cwm_%s_Water.pdb' % protein)):
                ProteinsList.proteins.remove(protein)

    logging.debug( '2. filtered ProteinsList.proteins is %s proteins long :' % len(ProteinsList.proteins) )

    """ 
        Filtered ProteinsList
    """

    selectedPDBChain = str(ProteinsList.selectedPDBChain)
    if len(ProteinsList.proteins) > 1:
        water_coordinates = list()
        waterIDCoordinates = {}
        water_ids = list()
        for protein in ProteinsList:
            protein.calculate_water_coordinates( temp_dir )
            logging.debug( 'protein %s coordinates length is :%i' % protein, len(protein.water_coordinates) )
            water_coordinates += protein.water_coordinates
            water_ids += protein.water_ids

        if water_coordinates:
            logging.info( 'number of water molecules to cluster : %i' % len(water_coordinates) )
            if len(water_coordinates) < 20000 and len(water_coordinates) != 1:
                logging.debug( 'clustering the water coordinates...' )
                # returns a list of clusternumbers
                FD = hcluster.fclusterdata(water_coordinates, 
                        t=ProteinsList.cluster_diameter, criterion='distance', 
                        metric='euclidean', depth=2, method='complete')
                FDlist = list(FD)
                fcDic = {}
                logging.debug( 'making flat cluster dictionary...' )
                for a,b in zip(water_ids,FDlist):
                    if fcDic.has_key(b):
                        fcDic[b].append(a)
                    else:
                        fcDic[b]=[a]

                conservedWaterDic = {}
                logging.debug( 'extracting conserved waters from clusters' )
                for clusterNumber, waterMols in fcDic.items():
                    waterMolsNumber = len(waterMols)
                    uniquePDBs = set([a[:6] for a in waterMols])
                    if selectedPDBChain in uniquePDBs:
                        uniquePDBslen = len(set([a[:6] for a in waterMols]))
                        if uniquePDBslen == waterMolsNumber:
                            probability = float(uniquePDBslen) / len(ProteinsList)
                            if probability > ProteinsList.probability:
                                logging.debug( 'probability is : %s' % probability )
                                for waterMol in waterMols:
                                    if conservedWaterDic.has_key(waterMol[:6]):
                                        conservedWaterDic[waterMol[:6]].append(waterMol[7:])
                                    else:
                                        conservedWaterDic[waterMol[:6]] = [waterMol[7:]]
                        elif uniquePDBslen < waterMolsNumber:
                            logging.debug( 'Warning : cutoff distance is too large...' )

                logging.debug( 'conservedWaterDic keys are: %s' % conservedWaterDic.keys() )
                if selectedPDBChain in conservedWaterDic.keys():
                    # save pdb file of conserved waters only for selected pdb
                    atomNumbers = conservedWaterDic[selectedPDBChain]
                    selectedPDBChainConservedWatersOut = open(os.path.join(temp_dir, 'cwm_'+selectedPDBChain+'_ConservedWatersOnly.pdb'),'w+')
                    selectedPDBChainIn = open(os.path.join(temp_dir, 'cwm_'+selectedPDBChain+'_Water.pdb'))
                    for line in selectedPDBChainIn:
                        if line.startswith('HETATM'):
                            if line.split()[1] in atomNumbers:
                                selectedPDBChainConservedWatersOut.write( line )
                    selectedPDBChainConservedWatersOut.write('END')
                    selectedPDBChainConservedWatersOut.close()

                    # add conserved waters to pdb file
                    cmd.delete('cwm_*')
                    cmd.load( os.path.join(temp_dir, 'cwm_%s.pdb' % selectedPDBChain) )
                    cmd.load( os.path.join(temp_dir, 'cwm_%s_ConservedWatersOnly.pdb' % selectedPDBChain) )
                    cmd.remove( 'resname hoh and '+'cwm_%s' % selectedPDBChain )
                    cmd.save( os.path.join(temp_dir, 'cwm_%s_withConservedWaters.pdb' % selectedPDBChain), 'cwm_*')
                    cmd.delete('cwm_*')
                    shutil.copy( os.path.join(temp_dir, 'cwm_%s_withConservedWaters.pdb' % selectedPDBChain), outdir)
                    shutil.copy(os.path.join(temp_dir, 'cwm_%s.pdb' % selectedPDBChain),outdir)
                else:
                    cmd.delete('cwm_*')
                    logging.debug( "%s has no conserved waters" % selectedPDBChain )
                    # save pdb without any water
                    cmd.load(os.path.join(temp_dir, 'cwm_%s.pdb' % selectedPDBChain))
                    cmd.remove('resname hoh and '+'cwm_%s' % selectedPDBChain)
                    cmd.save(os.path.join(temp_dir, 'cwm_%s_withConservedWaters.pdb' % selectedPDBChain),'cwm_*')
                    cmd.delete('cwm_*')
                    shutil.copy(os.path.join(temp_dir, 'cwm_%s_withConservedWaters.pdb' % selectedPDBChain), outdir)
                    shutil.copy(os.path.join(temp_dir, 'cwm_%s.pdb' % selectedPDBChain), outdir)
            else:
                logging.error( "%s has too many waters to cluster. Memory is not enough... OR only one water molecule..." % selectedPDBChain )
        else:
            cmd.delete('cwm_*')
            logging.info( "%s and other structures from the same CD-HIT cluster do not have any water molecules." % selectedPDBChain )
            # save pdb without any water
            cmd.load(os.path.join(temp_dir, 'cwm_%s.pdb' % selectedPDBChain))
            cmd.remove('resname hoh and cwm_%s' % selectedPDBChain)
            cmd.save(os.path.join(temp_dir, 'cwm_%s_withConservedWaters.pdb' % selectedPDBChain), 'cwm_*')
            cmd.delete('cwm_*')
            shutil.copy(os.path.join(temp_dir, 'cwm_%s_withConservedWaters.pdb' % selectedPDBChain), outdir)
    else:
        logging.error( "%s has only one PDB structure. We need atleast 2 structures to superimpose." % selectedPDBChain )
    if os.path.exists(os.path.join(outdir, 'cwm_%s_withConservedWaters.pdb' % selectedPDBChain)):
        displayInPyMOL(outdir, 'cwm_%s' % selectedPDBChain)


def fetchpdbChainsList(selectedStruture,seq_id):
    pdbChainsList = []
    seqClustAddress = 'http://pdb.org/pdb/rest/sequenceCluster?cluster=%d&structureId=%s' % (seq_id, selectedStruture) #http://pdb.org/pdb/rest/sequenceCluster?cluster=95&structureId=3qkl.A
    seqClustURL = urllib.urlopen(seqClustAddress)
    toursurl_string= seqClustURL.read()
    if toursurl_string.startswith('An error has occurred'):
        return pdbChainsList
    else:
        seqCluster = parseString( toursurl_string )
        for xmlTag in seqCluster.getElementsByTagName('pdbChain'):
            pdbChainsList.append(str(xmlTag.getAttribute('name')).replace('.', ':'))
        return pdbChainsList

def filterbyResolution(pdbChainsList,resolutionCutoff):
    pdbsList = []
    for pdbChain in pdbChainsList:
        pdbsList.append(pdbChain.split(':')[0])
    pdbsList =list(set(pdbsList))

    filteredpdbChainsList = []
    pdbsResolution = {}
    for pdb in pdbsList:
        getResolutionAddress ='http://pdb.org/pdb/rest/customReport?pdbids=%s&customReportColumns=resolution&service=wsfile&format=xml&ssa=n' % (pdb)
        pdbsResolution_string = urllib.urlopen(getResolutionAddress).read()
        pdbsResolutionXML = parseString(pdbsResolution_string)
        pdbsResolution[pdb] = str(pdbsResolutionXML.getElementsByTagName('dimStructure.resolution')[0].childNodes[0].nodeValue)

    for pdbChain in pdbChainsList:
        if pdbsResolution[pdbChain.split(':')[0]] != 'null':
            if float(pdbsResolution[pdbChain.split(':')[0]]) <= resolutionCutoff:
                filteredpdbChainsList.append(pdbChain)

    return filteredpdbChainsList


def FindConservedWaters(selectedStruturePDB,selectedStrutureChain,seq_id,resolution,refinement,cluster_diameter,prob):# e.g: selectedStruturePDB='3qkl',selectedStrutureChain='A'
    if not re.compile('^[a-z0-9]{4}$').match(selectedStruturePDB):
        logging.info( 'The entered PDB id is not valid.' )
        tkMessageBox.showinfo(title = 'Error message', 
            message = """The entered PDB id is not valid.""")
        return None
    if not re.compile('[A-Z]').match(selectedStrutureChain):
        logging.info( 'The entered PDB chain id is not valid.' )
        tkMessageBox.showinfo(title = 'Error message', 
            message = """The entered PDB chain id is not valid.""")
        return None
    if resolution > 3.0:
        logging.info( 'The maximum allowed resolution cutoff is 3.0 A' )
        tkMessageBox.showinfo(title = 'Error message', 
            message = """The maximum allowed resolution cutoff is 3.0 A.""")
        return None
    if cluster_diameter > 2.4:
        logging.info( 'The maximum allowed cluster diameter is 2.4 A' )
        tkMessageBox.showinfo(title = 'Error message', 
            message = """The maximum allowed cluster diameter is 2.4 A.""")
        return None
    if prob > 1.0 or prob < 0.4:
        logging.info( 'The probability cutoff is allowed from 0.4 A to 1.0 A.' )
        tkMessageBox.showinfo(title = 'Error message', 
            message = """The probability cutoff is allowed from 0.4 A to 1.0 A.""")
        return None
    online_pdb_db = 'http://www.pdb.org/pdb/files/%s.pdb'
    displayInputs(selectedStruturePDB, selectedStrutureChain, seq_id, resolution, cluster_diameter, prob)
    tmp_dir = tempfile.mkdtemp()
    outdir = tempfile.mkdtemp( dir = tmp_dir )

    selectedStruture = ".".join([selectedStruturePDB.lower(),selectedStrutureChain.upper()]) # 3qkl:A
    up = ProteinsList(ProteinName = selectedStruture) # ProteinsList class instance up
    up.refinement = refinement
    up.probability = prob
    up.cluster_diameter = cluster_diameter
    logging.info( 'selectedStruture is : %s' selectedStruture )
    up.selectedPDBChain = Protein(selectedStruturePDB, selectedStrutureChain) # up.selectedPDBChain = 3qkl_a
    logging.info( 'up selectedPDBChain is : %s' % up.selectedPDBChain )
    selectedPDBChain = str(up.selectedPDBChain)
    logging.info( 'selectedPDBChain name is : %s' % selectedPDBChain )
    pdbChainsList = fetchpdbChainsList(selectedStruture,seq_id) # ['3QKL:A', '4EKL:A', '3QKM:A', '3QKK:A', '3OW4:A', '3OW4:B', '3OCB:A', '3OCB:B', '4EKK:A', '4EKK:B']
    logging.info( 'pdbChainsList contains %i pdb chains.' % len(pdbChainsList)
    pdbChainsList = filterbyResolution(pdbChainsList,resolution)
    logging.info( 'Filtered pdbChainsList contains %i pdb chains.' % len(pdbChainsList)
    for pdbChain in pdbChainsList:
        up.add_protein_from_string(pdbChain)
    logging.debug( 'up is : %s' % up.proteins ) #[3qkl_a, 4ekl_a, 3qkm_a, 3qkk_a, 3ow4_a, 3ow4_b, 3ocb_a, 3ocb_b, 4ekk_a, 4ekk_b]
    if len(up.proteins)>1:
        logging.debug( 'length of ProteinsList is : %s' % len(up.proteins) )
        for protein in up:
            logging.debug( protein )
            logging.debug( protein.pdb_id )
            if not os.path.exists(os.path.join(tmp_dir, '%s.pdb' % protein.pdb_id)):
                logging.debug( 'retrieving pdb from website : %s' % protein.pdb_id)
                urllib.urlretrieve(online_pdb_db % protein.pdb_id.upper(), os.path.join(tmp_dir, protein.pdb_id+'.pdb'))
        logging.info( 'making pdb with conserved waters...' )
        makePDBwithConservedWaters(up, tmp_dir, outdir)
    else:
        logging.info( "%s has only one PDB structure. We need atleast 2 structures to superimpose." % selectedPDBChain)

    shutil.rmtree(temp_dir)


class ConservedWaters(Frame):
    def __init__(self,parent):
        Frame.__init__(self, parent, background="white")
        self.parent=parent
        self.parent.title("PyCWMs - Find Conserved Waters")
        self.grid()
        self.makeWindow()

    def makeWindow(self):
        frame1 = Frame(self.parent)
        frame1.grid()

        Label(frame1, text="PDB id").grid(row=0, column=0, sticky=W)
        Button(frame1,text=" Help  ",command=pdb_id_help).grid(row=0, column=2, sticky=W)
        v1 = StringVar(master=frame1)
        v1.set('')
        Entry(frame1,textvariable=v1).grid(row=0, column=1, sticky=W)

        Label(frame1, text="Chain").grid(row=1, column=0, sticky=W)
        Button(frame1,text=" Help  ",command=chain_help).grid(row=1, column=2, sticky=W)
        v2 = StringVar(master=frame1)
        v2.set('')
        Entry(frame1,textvariable=v2).grid(row=1, column=1, sticky=W)

        Label(frame1, text="Sequence identity cutoff").grid(row=2, column=0, sticky=W)
        Button(frame1,text=" Help  ",command=seq_id_help).grid(row=2, column=2, sticky=W)
        v3 = StringVar(master=frame1)
        v3.set("95")
        OptionMenu(frame1, v3, '30', '40','50', '70','90','95','100').grid(row=2, column=1, sticky=W)

        Label(frame1, text="Structure resolution cutoff").grid(row=3, column=0, sticky=W)
        Button(frame1,text=" Help  ",command=resolution_help).grid(row=3, column=2, sticky=W)
        v4 = StringVar(master=frame1)
        v4.set("2.0")
        Entry(frame1,textvariable=v4).grid(row=3, column=1, sticky=W)

        Label(frame1, text="Filter by refinement quality using").grid(row=4, column=0, sticky=W)
        Button(frame1,text=" Help  ",command=refinement_quality_help).grid(row=4, column=2, sticky=W)
        v5 = StringVar(master=frame1)
        v5.set('Mobility')
        OptionMenu(frame1, v5, 'Mobility', 'Normalized B-factors').grid(row=4, column=1, sticky=W)

        Label(frame1, text="Custer diameter").grid(row=5, column=0, sticky=W)
        Button(frame1,text=" Help  ",command=cluster_diameter_help).grid(row=5, column=2, sticky=W)
        v6 = StringVar(master=frame1)
        v6.set("1.5")
        Entry(frame1,textvariable=v6).grid(row=5, column=1, sticky=W)

        Label(frame1, text="Probability cutoff").grid(row=6, column=0, sticky=W)
        Button(frame1,text=" Help  ",command=prob_help).grid(row=6, column=2, sticky=W)
        v7 = StringVar(master=frame1)
        v7.set("0.7")
        Entry(frame1,textvariable=v7).grid(row=6, column=1, sticky=W)

        frame2 = Frame(self.parent)
        frame2.grid()

        Button(frame2,text=" Find Conserved Water Molecules ",
            command = lambda: FindConservedWaters(str(v1.get()).lower(),str(v2.get()).upper(),int(v3.get()),float(v4.get()),str(v5.get()),float(v6.get()),float(v7.get()))).grid(row=0, column=1, sticky=W)

def main():
    root = Tk()
    app = ConservedWaters(root)
    root.mainloop()  

if __name__ == '__main__':
    main()

