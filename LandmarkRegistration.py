import os
import unittest
from __main__ import vtk, qt, ctk, slicer

#
# LandmarkRegistration
#

class LandmarkRegistration:
  def __init__(self, parent):
    parent.title = "Landmark Registration"
    parent.categories = ["Registration"]
    parent.dependencies = []
    parent.contributors = ["Steve Pieper (Isomics)"] # replace with "Firstname Lastname (Org)"
    parent.helpText = """
    This module organizes a fixed and moving volume along with a set of corresponding
    landmarks (paired fiducials) to assist in manual registration.
    """
    parent.acknowledgementText = """
    This file was developed by Steve Pieper, Isomics, Inc.
    It was partially funded by NIH grant 3P41RR013218-12S1
    and this work is part of the National Alliance for Medical Image
    Computing (NAMIC), funded by the National Institutes of Health
    through the NIH Roadmap for Medical Research, Grant U54 EB005149.
    Information on the National Centers for Biomedical Computing
    can be obtained from http://nihroadmap.nih.gov/bioinformatics.
    """ # replace with organization, grant and thanks.
    self.parent = parent

    # Add this test to the SelfTest module's list for discovery when the module
    # is created.  Since this module may be discovered before SelfTests itself,
    # create the list if it doesn't already exist.
    try:
      slicer.selfTests
    except AttributeError:
      slicer.selfTests = {}
    slicer.selfTests['LandmarkRegistration'] = self.runTest

  def runTest(self):
    tester = LandmarkRegistrationTest()
    tester.runTest()

#
# qLandmarkRegistrationWidget
#

class LandmarkRegistrationWidget:
  """The module GUI widget"""
  def __init__(self, parent = None):
    self.logic = LandmarkRegistrationLogic()
    self.sliceNodesByViewName = {}

    if not parent:
      self.parent = slicer.qMRMLWidget()
      self.parent.setLayout(qt.QVBoxLayout())
      self.parent.setMRMLScene(slicer.mrmlScene)
    else:
      self.parent = parent
    self.layout = self.parent.layout()
    if not parent:
      self.setup()
      self.parent.show()

  def setup(self):
    # Instantiate and connect widgets ...

    #
    # Reload and Test area
    #
    reloadCollapsibleButton = ctk.ctkCollapsibleButton()
    reloadCollapsibleButton.text = "Reload && Test"
    self.layout.addWidget(reloadCollapsibleButton)
    reloadFormLayout = qt.QFormLayout(reloadCollapsibleButton)

    # reload button
    # (use this during development, but remove it when delivering
    #  your module to users)
    self.reloadButton = qt.QPushButton("Reload")
    self.reloadButton.toolTip = "Reload this module."
    self.reloadButton.name = "LandmarkRegistration Reload"
    reloadFormLayout.addWidget(self.reloadButton)
    self.reloadButton.connect('clicked()', self.onReload)

    # reload and test button
    # (use this during development, but remove it when delivering
    #  your module to users)
    self.reloadAndTestButton = qt.QPushButton("Reload and Test")
    self.reloadAndTestButton.toolTip = "Reload this module and then run the self tests."
    reloadFormLayout.addWidget(self.reloadAndTestButton)
    self.reloadAndTestButton.connect('clicked()', self.onReloadAndTest)

    #
    # Parameters Area
    #
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = "Parameters"
    self.layout.addWidget(parametersCollapsibleButton)

    # Layout within the dummy collapsible button
    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

    self.volumeSelectors = {}
    viewNames = ("Moving", "Fixed", "Warped")
    for viewName in viewNames:
      self.volumeSelectors[viewName] = slicer.qMRMLNodeComboBox()
      self.volumeSelectors[viewName].nodeTypes = ( ("vtkMRMLScalarVolumeNode"), "" )
      self.volumeSelectors[viewName].selectNodeUponCreation = False
      self.volumeSelectors[viewName].addEnabled = False
      self.volumeSelectors[viewName].removeEnabled = True
      self.volumeSelectors[viewName].noneEnabled = True
      self.volumeSelectors[viewName].showHidden = False
      self.volumeSelectors[viewName].showChildNodeTypes = True
      self.volumeSelectors[viewName].setMRMLScene( slicer.mrmlScene )
      self.volumeSelectors[viewName].setToolTip( "Pick the %s volume." % viewName.lower() )
      parametersFormLayout.addRow("%s Volume: " % viewName, self.volumeSelectors[viewName])

    self.volumeSelectors["Warped"].addEnabled = True
    self.volumeSelectors["Warped"].setToolTip( "Pick the warped volume, which is the target for the registration." )

    #
    # layout options
    #
    layout = qt.QHBoxLayout()
    self.layoutComboBox = qt.QComboBox()
    self.layoutComboBox.addItem('Axial')
    self.layoutComboBox.addItem('Sagittal')
    self.layoutComboBox.addItem('Coronal')
    #self.layoutComboBox.addItem('Axial/Sagittal/Coronal')
    #self.layoutComboBox.addItem('Ax/Sag/Cor/3D')
    layout.addWidget(self.layoutComboBox)
    self.layoutButton = qt.QPushButton('Layout')
    self.layoutButton.connect('clicked()', self.onLayout)
    layout.addWidget(self.layoutButton)
    parametersFormLayout.addRow("Layout Mode: ", layout)

    #
    # Landmark Widget
    #
    self.landmarks = Landmarks(self.logic)
    parametersFormLayout.addRow(self.landmarks.widget)

    #
    # Apply Button
    #
    self.applyButton = qt.QPushButton("Run Registration")
    self.applyButton.toolTip = "Run the registration algorithm."
    self.applyButton.enabled = False
    parametersFormLayout.addRow(self.applyButton)

    # connections
    self.applyButton.connect('clicked(bool)', self.onApplyButton)
    for selector in self.volumeSelectors.values():
      selector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)

    # Add vertical spacer
    self.layout.addStretch(1)

  def currentVolumeNodes(self):
    """List of currently selected volume nodes"""
    volumeNodes = []
    for selector in self.volumeSelectors.values():
      volumeNode = selector.currentNode()
      if volumeNode:
        volumeNodes.append(volumeNode)
    return(volumeNodes)

  def onSelect(self):
    """When one of the volume selectors is changed"""
    volumeNodes = self.currentVolumeNodes()
    self.landmarks.setVolumeNodes(volumeNodes)

  def onLayout(self):
    volumeNodes = []
    viewNames = []
    for name, selector in self.volumeSelectors.iteritems():
      volumeNode = selector.currentNode()
      if volumeNode:
        volumeNodes.append(volumeNode)
        viewNames.append(name)
    mode = self.layoutComboBox.currentText
    import CompareVolumes
    compareLogic = CompareVolumes.CompareVolumesLogic()
    oneViewModes = ('Axial', 'Sagittal', 'Coronal',)
    if mode in oneViewModes:
      self.sliceNodesByViewName = compareLogic.viewerPerVolume(volumeNodes,viewNames=viewNames,orientation=mode)
    self.restrictLandmarksToViews()

  def restrictLandmarksToViews(self):
    """Set fiducials so they only show up in the view
    for the volume on which they were defined"""
    volumeNodes = self.currentVolumeNodes()
    if self.sliceNodesByViewName:
      sliceNodesByVolumeID = {}
      for viewName,sliceNode in self.sliceNodesByViewName.iteritems():
        volumeID = self.volumeSelectors[viewName].currentNodeId
        sliceNodesByVolumeID[volumeID] = sliceNode
      landmarks = self.logic.landmarksForVolumes(volumeNodes)
      for fidList in landmarks.values():
        for fid in fidList:
          volumeNodeID = fid.GetAttribute("AssociatedNodeID")
          if volumeNodeID:
            if sliceNodesByVolumeID.has_key(volumeNodeID):
              displayNode = fid.GetDisplayNode()
              displayNode.RemoveAllViewNodeIDs()
              displayNode.AddViewNodeID(sliceNodesByVolumeID[volumeNodeID].GetID())

  def onApplyButton(self):
    print("Run the algorithm")
    #self.logic.run(self.fixedSelector.currentNode(), self.movingSelector.currentNode())

  def onReload(self,moduleName="LandmarkRegistration"):
    """Generic reload method for any scripted module.
    ModuleWizard will subsitute correct default moduleName.
    """
    import imp, sys, os, slicer

    widgetName = moduleName + "Widget"

    # reload the source code
    # - set source file path
    # - load the module to the global space
    filePath = eval('slicer.modules.%s.path' % moduleName.lower())
    p = os.path.dirname(filePath)
    if not sys.path.__contains__(p):
      sys.path.insert(0,p)
    fp = open(filePath, "r")
    globals()[moduleName] = imp.load_module(
        moduleName, fp, filePath, ('.py', 'r', imp.PY_SOURCE))
    fp.close()

    # rebuild the widget
    # - find and hide the existing widget
    # - create a new widget in the existing parent
    parent = slicer.util.findChildren(name='%s Reload' % moduleName)[0].parent().parent()
    for child in parent.children():
      try:
        child.hide()
      except AttributeError:
        pass
    # Remove spacer items
    item = parent.layout().itemAt(0)
    while item:
      parent.layout().removeItem(item)
      item = parent.layout().itemAt(0)
    # create new widget inside existing parent
    globals()[widgetName.lower()] = eval(
        'globals()["%s"].%s(parent)' % (moduleName, widgetName))
    globals()[widgetName.lower()].setup()

  def onReloadAndTest(self,moduleName="LandmarkRegistration"):
    try:
      self.onReload()
      evalString = 'globals()["%s"].%sTest()' % (moduleName, moduleName)
      tester = eval(evalString)
      tester.runTest()
    except Exception, e:
      import traceback
      traceback.print_exc()
      qt.QMessageBox.warning(slicer.util.mainWindow(),
          "Reload and Test", 'Exception!\n\n' + str(e) + "\n\nSee Python Console for Stack Trace")


class Landmarks:
  """
  A "QWidget"-like class that manages a set of landmarks
  that are pairs of fiducials
  """

  def __init__(self,logic):
    self.logic = logic
    self.volumeNodes = []
    self.selectedLandmark = None # a landmark name
    self.landmarkGroupBox = None # a QGroupBox
    self.buttons = {} # the current buttons in the group box

    self.widget = qt.QWidget()
    self.layout = qt.QFormLayout(self.widget)
    self.landmarkArrayHolder = qt.QWidget()
    self.landmarkArrayHolder.setLayout(qt.QVBoxLayout())
    self.layout.addRow(self.landmarkArrayHolder)
    self.updateLandmarkArray()

  def setVolumeNodes(self,volumeNodes):
    """Set up the widget to reflect the currently selected
    volume nodes.  This triggers an update of the landmarks"""
    self.volumeNodes = volumeNodes
    self.updateLandmarkArray()

  def updateLandmarkArray(self):
    """Rebuild the list of buttons based on current landmarks"""
    # reset the widget
    if self.landmarkGroupBox:
      self.landmarkGroupBox.setParent(None)
    self.landmarkGroupBox = qt.QGroupBox("Landmarks")
    self.landmarkGroupBox.setLayout(qt.QFormLayout())
    # add the action buttons at the top
    actionButtons = qt.QHBoxLayout()
    self.addButton = qt.QPushButton("Add")
    self.addButton.connect('clicked()', self.addLandmark)
    actionButtons.addWidget(self.addButton)
    self.removeButton = qt.QPushButton("Remove")
    self.removeButton.connect('clicked()', self.removeLandmark)
    self.removeButton.enabled = False
    actionButtons.addWidget(self.removeButton)
    self.renameButton = qt.QPushButton("Rename")
    self.renameButton.connect('clicked()', self.renameLandmark)
    self.renameButton.enabled = False
    actionButtons.addWidget(self.renameButton)
    self.landmarkGroupBox.layout().addRow(actionButtons)
    self.buttons = {}

    # make a button for each current landmark
    landmarks = self.logic.landmarksForVolumes(self.volumeNodes)
    for landmarkName in landmarks.keys():
      button = qt.QPushButton(landmarkName)
      button.connect('clicked()', lambda l=landmarkName: self.pickLandmark(l))
      self.landmarkGroupBox.layout().addRow( button )
      self.buttons[landmarkName] = button
    self.landmarkArrayHolder.layout().addWidget(self.landmarkGroupBox)

  def pickLandmark(self,landmarkName):
    for key in self.buttons.keys():
      self.buttons[key].text = key
    self.buttons[landmarkName].text = '*' + landmarkName
    self.selectedLandmark = landmarkName
    self.renameButton.enabled = True
    self.removeButton.enabled = True

  def addLandmark(self):
    import time
    newLandmark = 'new' + str(time.time())
    self.landmarks.append(newLandmark)
    self.updateLandmarkArray()
    self.pickLandmark(newLandmark)

  def removeLandmark(self):
    self.landmarks.remove(self.selectedLandmark)
    self.selectedLandmark = None
    self.updateLandmarkArray()

  def renameLandmark(self):
    newName = qt.QInputDialog.getText(
        slicer.util.mainWindow(), "Rename Landmark",
        "New name for landmark '%s'?" % self.selectedLandmark)
    if newName != "":
      self.landmarks[self.landmarks.index(self.selectedLandmark)] = newName
      self.selectedLandmark = newName
      self.updateLandmarkArray()
      self.pickLandmark(newName)



#
# LandmarkRegistrationLogic
#

class LandmarkRegistrationLogic:
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget
  """
  def __init__(self):
    pass

  def addFiducial(self,name,position=(0,0,0),associatedNode=None):
    """Add an instance of a fiducial to the scene for a given
    volume node"""

    annoLogic = slicer.modules.annotations.logic()
    slicer.mrmlScene.StartState(slicer.mrmlScene.BatchProcessState)

    # make the fiducial list if required
    listName = associatedNode.GetName() + "-landmarks"
    fidListHierarchyNode = slicer.util.getNode(listName)
    if not fidListHierarchyNode:
      fidListHierarchyNode = slicer.vtkMRMLAnnotationHierarchyNode()
      fidListHierarchyNode.HideFromEditorsOff()
      fidListHierarchyNode.SetName(listName)
      slicer.mrmlScene.AddNode(fidListHierarchyNode)
      # make it a child of the top level node
      fidListHierarchyNode.SetParentNodeID(annoLogic.GetTopLevelHierarchyNodeID())
    # make this active so that the fids will be added to it
    annoLogic.SetActiveHierarchyNodeID(fidListHierarchyNode.GetID())

    fiducialNode = slicer.vtkMRMLAnnotationFiducialNode()
    if associatedNode:
      fiducialNode.SetAttribute("AssociatedNodeID", associatedNode.GetID())
    fiducialNode.SetName(name)
    fiducialNode.AddControlPoint(position, True, True)
    fiducialNode.SetSelected(True)
    fiducialNode.SetLocked(False)
    slicer.mrmlScene.AddNode(fiducialNode)

    fiducialNode.CreateAnnotationTextDisplayNode()
    fiducialNode.CreateAnnotationPointDisplayNode()
    # TODO: pick appropriate defaults
    # 135,135,84
    fiducialNode.SetTextScale(2.)
    fiducialNode.GetAnnotationPointDisplayNode().SetGlyphScale(2)
    fiducialNode.GetAnnotationPointDisplayNode().SetGlyphTypeFromString('StarBurst2D')
    fiducialNode.SetDisplayVisibility(True)

    slicer.mrmlScene.EndState(slicer.mrmlScene.BatchProcessState)

  def volumeFiducialsAsList(self,volumeNode):
    """return a list of annotation nodes that are
    children of the list associated with the given 
    volume node"""
    children = []
    listName = volumeNode.GetName() + "-landmarks"
    fidListHierarchyNode = slicer.util.getNode(listName)
    if fidListHierarchyNode:
      childCollection = vtk.vtkCollection()
      fidListHierarchyNode.GetAllChildren(childCollection)
      for childIndex in range(childCollection.GetNumberOfItems()):
        children.append(childCollection.GetItemAsObject(childIndex))
    return children

  def landmarksForVolumes(self,volumeNodes):
    """Return a dictionary of fiducial node lists, where each element
    is a list of the ids of fiducials with matching names in 
    the landmark lists for each of the given volumes.
    Only fiducials that exist for all volumes are returned."""
    fiducialsByName = {}
    for volumeNode in volumeNodes:
      children = self.volumeFiducialsAsList(volumeNode)
      for child in children:
        if fiducialsByName.has_key(child.GetName()):
          fiducialsByName[child.GetName()].append(child)
        else:
          fiducialsByName[child.GetName()] = [child,]
    for childName in fiducialsByName.keys():
      if len(fiducialsByName[childName]) != len(volumeNodes):
        fiducialsByName.__delitem__(childName)
    return fiducialsByName




  def run(self,inputVolume,outputVolume):
    """
    Run the actual algorithm
    """
    return True


class LandmarkRegistrationTest(unittest.TestCase):
  """
  This is the test case for your scripted module.
  """

  def delayDisplay(self,message,msec=1000):
    """This utility method displays a small dialog and waits.
    This does two things: 1) it lets the event loop catch up
    to the state of the test so that rendering and widget updates
    have all taken place before the test continues and 2) it
    shows the user/developer/tester the state of the test
    so that we'll know when it breaks.
    """
    print(message)
    self.info = qt.QDialog()
    self.infoLayout = qt.QVBoxLayout()
    self.info.setLayout(self.infoLayout)
    self.label = qt.QLabel(message,self.info)
    self.infoLayout.addWidget(self.label)
    qt.QTimer.singleShot(msec, self.info.close)
    self.info.exec_()

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_LandmarkRegistration1()

  def test_LandmarkRegistration1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests sould exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #
    import SampleData
    sampleDataLogic = SampleData.SampleDataLogic()
    mrHead = sampleDataLogic.downloadMRHead()
    dtiBrain = sampleDataLogic.downloadDTIBrain()
    self.delayDisplay('Two data sets loaded')

    w = LandmarkRegistrationWidget()
    w.volumeSelectors["Fixed"].setCurrentNode(mrHead)
    w.volumeSelectors["Moving"].setCurrentNode(dtiBrain)

    logic = LandmarkRegistrationLogic()
    landmark = logic.addFiducial("tip-of-nose", position=(10, 0, -.5),associatedNode=mrHead)
    landmark = logic.addFiducial("middle-of-left-eye", position=(30, 0, -.5),associatedNode=mrHead)

    landmark = logic.addFiducial("tip-of-nose", position=(0, 0, 0),associatedNode=dtiBrain)
    landmark = logic.addFiducial("middle-of-left-eye", position=(23, 0, -.95),associatedNode=dtiBrain)

    self.delayDisplay('Test passed!')