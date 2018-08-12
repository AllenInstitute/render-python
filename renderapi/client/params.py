from renderapi.errors import ClientScriptError


class ArgumentParameters(object):
    def __init__(self, *args, **kwargs):
        pass

    @staticmethod
    def sanitize_cmd(cmd):
        def jbool_str(c):
            return str(c) if type(c) is not bool else "true" if c else "false"
        if any([i is None for i in cmd]):
            raise ClientScriptError(
                'missing argument in command "{}"'.format(map(str, cmd)))
        return map(jbool_str, cmd)

    @staticmethod
    def get_cmd_opt(v, flag=None):
        return [] if v is None else [v] if flag is None else [flag, v]

    @staticmethod
    def get_flag_cmd(v, flag=None):
        # for arity 0
        return [flag] if v else []

    def to_java_args(self):
        args = []
        for key, value in self.__dict__.items():
            if (value is not None) and not (key == 'kwargs'):
                args += self.get_cmd_opt(value, "--{}".format(key))
        return self.sanitize_cmd(args)


class FeatureExtractionParameters(ArgumentParameters):
    def __init__(self, SIFTfdSize=None, SIFTmaxScale=None,
                 SIFTminScale=None, SIFTsteps=None, **kwargs):
        super(FeatureExtractionParameters, self).__init__(**kwargs)
        self.SIFTfdSize = SIFTfdSize
        self.SIFTmaxScale = SIFTmaxScale
        self.SIFTminScale = SIFTminScale
        self.SIFTsteps = SIFTsteps


class MatchDerivationParameters(ArgumentParameters):
    def __init__(self, matchIterations=None,
                 matchMaxEpsilon=None, matchMaxNumInliers=None,
                 matchMaxTrust=None, matchMinInlierRatio=None,
                 matchMinNumInliers=None,
                 matchModelType=None, matchRod=None, **kwargs):
        super(MatchDerivationParameters, self).__init__(**kwargs)
        self.matchIterations = matchIterations
        self.matchMaxEpsilon = matchMaxEpsilon
        self.matchMaxNumInliers = matchMaxNumInliers
        self.matchMaxTrust = matchMaxTrust
        self.matchMinInlierRatio = matchMinInlierRatio
        self.matchMinNumInliers = matchMinNumInliers
        self.matchMinNumInliers = matchMinNumInliers
        self.matchModelType = matchModelType
        self.matchRod = matchRod


class SiftPointMatchOptions(MatchDerivationParameters,
                            FeatureExtractionParameters):
    def __init__(self, renderScale=None, fillWithNoise=None, **kwargs):
        # TODO add missing parameters
        super(SiftPointMatchOptions, self).__init__(**kwargs)
        self.renderScale = renderScale
        self.fillWithNoise = fillWithNoise
