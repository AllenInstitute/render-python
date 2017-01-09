from PIL import Image
import argparse
import os
from tilespec import TileSpec

#def add_mipmaps_to_tilespec(tilespec):
    

def create_mipmaps(inputImage,outputDirectory='.',mipmaplevels=[1,2,3],outputformat='jpg'):
    if not os.path.isdir(outputDirectory):
        os.makedirs(outputDirectory)

    im = Image.open(inputImage)
    #print 'origmode',im.mode
    origsize = im.size
    table=[ i/256 for i in range(65536) ]
    im = im.convert('I')
    im = im.point(table,'L')
    #print 'new mode',im.mode
    inputFileName = os.path.split(inputImage)[1]
                   
    for level in mipmaplevels:
        newsize = tuple(map(lambda x: x/(2**level), origsize))
        dwnImage = im.resize(newsize)
        outpath = os.path.join(outputDirectory,inputFileName[0:-4]+'_mip%02d.'%level+outputformat)
        dwnImage.save(outpath)
        print outpath,level,newsize

        
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Create downsampled images of the input image at different midmap levels")

    parser.add_argument('--inputImage', help="Path to the input image.")
    parser.add_argument('--outputDirectory',help="Path to save midmap images",default = None)
    parser.add_argument('--mipmaplevels',nargs='*',help="mipmaplevels to generate",default = [1,2,3],type=int)
    parser.add_argument('--outputformat',help="format to save images",default = 'jpg')
    parser.add_argument('--verbose',help="verbose output",default=False,action="store_true")

    args = parser.parse_args()
    
    print 'outdir',args.outputDirectory
    if args.outputDirectory is None:
        args.outputDirectory = os.path.split(args.inputImage)[0]
        if len(args.outputDirectory)==0:
            args.outputDirectory='.'

    create_mipmaps(args.inputImage,args.outputDirectory,args.mipmaplevels,args.outputformat)
    
#     if not os.path.isdir(args.outputDirectory):
#         os.makedirs(args.outputDirectory)

#     im = Image.open(args.inputImage)
#     print 'origmode',im.mode
#     origsize = im.size
#     table=[ i/256 for i in range(65536) ]
#     im = im.convert('I')
#     im = im.point(table,'L')
#     print 'new mode',im.mode
#     inputFileName = os.path.split(args.inputImage)[1]
                   
#     for level in args.mipmaplevels:
#         newsize = tuple(map(lambda x: x/(2**level), origsize))
#         dwnImage = im.resize(newsize)
#         outpath = os.path.join(args.outputDirectory,inputFileName[0:-4]+'_mip%02d.'%level+args.outputformat)
#         dwnImage.save(outpath)
#         print outpath,level,newsize
        
    
