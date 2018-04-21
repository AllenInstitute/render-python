class Layout:
    """Layout class to describe acquisition settings

    Attributes
    ----------
    sectionId : str
        sectionId this tile was taken from
    scopeId : str
        what microscope this came from
    cameraId : str
        camera this was taken with
    imageRow : int
        what row from a row,col layout this was taken
    imageCol : int
        column from a row,col layout this was taken
    stageX : float
        X stage coordinates for where this was taken
    stageY : float
        Y stage coordinates for where this taken
    rotation : float
        angle of camera when this was taken
    pixelsize : float
        effective size of pixels (in units of choice)

    """
    def __init__(self, sectionId=None, scopeId=None, cameraId=None,
                 imageRow=None, imageCol=None, stageX=None, stageY=None,
                 rotation=None, pixelsize=None,
                 force_pixelsize=True, **kwargs):
        """Initialize Layout

        Parameters
        ----------
        sectionId : str
            sectionId this tile was taken from
        scopeId : str
            what microscope this came from
        cameraId : str
            camera this was taken with
        imageRow : int
            what row from a row,col layout this was taken
        imageCol : int
            column from a row,col layout this was taken
        stageX : float
            X stage coordinates for where this was taken
        stageY : float
            Y stage coordinates for where this taken
        rotation : float
            angle of camera when this was taken
        pixelsize : float
            effective size of pixels (in units of choice)
        force_pixelsize : bool
            whether to default pixelsize to 0.1

        """
        self.sectionId = sectionId
        self.scopeId = scopeId
        self.cameraId = cameraId
        self.imageRow = imageRow
        self.imageCol = imageCol
        self.stageX = stageX
        self.stageY = stageY
        self.rotation = rotation
        if force_pixelsize:
            pixelsize = 0.100 if pixelsize is None else pixelsize
        self.pixelsize = pixelsize

    def to_dict(self):
        """return a dictionary representation of this object

        Returns
        -------
        dict
            json compatible dictionary of this object
        """
        d = {}
        d['sectionId'] = self.sectionId
        d['temca'] = self.scopeId
        d['camera'] = self.cameraId
        d['imageRow'] = self.imageRow
        d['imageCol'] = self.imageCol
        d['stageX'] = self.stageX
        d['stageY'] = self.stageY
        d['rotation'] = self.rotation
        d['pixelsize'] = self.pixelsize
        d = {k: v for k, v in d.items() if v is not None}
        return d

    def from_dict(self, d):
        """set this object equal to the fields found in dictionary

        Parameters
        ----------
        d : dict
            dictionary to use to update
        """
        if d is not None:
            self.sectionId = d.get('sectionId')
            self.cameraId = d.get('camera')
            self.scopeId = d.get('temca')
            self.imageRow = d.get('imageRow')
            self.imageCol = d.get('imageCol')
            self.stageX = d.get('stageX')
            self.stageY = d.get('stageY')
            self.rotation = d.get('rotation')
            self.pixelsize = d.get('pixelsize')
