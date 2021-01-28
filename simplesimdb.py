"""Creation and management of simple simulation data"""
import json
import hashlib # for the hashing
import os.path # to check for files
import subprocess # to run the create program

class Manager :
    """ Simulation database manager

    Create, access and display simulation data of a given code as pairs
    (inputfile.json : outputfile), where all input files
    are json files (converted from python dictionaries) and the output files (of
    arbitrary type) are generated by an executable that takes the json file as
    input. This executable is provided by the user and could for example
    be the program itself or a script calling it. The idea is to let the user
    define how the code should be run.
    """

    def __init__ (self, directory = './data', filetype='nc', executable="./execute.sh"):
        """ init the Manager class

        Parameters
        directory (path) : the path of the folder this class manages.
            Folder is created if it does not exist yet.  The class will
            recognize existing files that were generated by a previous session.
        filetype (string) : file extension of the output files
        executable (string) : The executable that generates the data

        This file will be called using subprocess.run([executable, id.json,
        id.filetype],...) that is it must take 2 arguments - a json file as
        input (do not change the input else the file is not recognized any
        more) and one output file (that executable needs to generate)
        (if your code does not take json as input you can for example parse
        json in bash using jq)
        """
        self.directory = directory
        os.makedirs( self.__directory, exist_ok=True)
        self.filetype = filetype
        self.executable = executable

    @property
    def directory(self):
        """ (path) : data directory

        If the directory does not exist it will be created """
        return self.__directory

    @property
    def executable(self):
        """
        (string) : The executable that generates the data.

        The create method calls subprocess.run([executable, id.json,
        id.filetype],...) that is it must take 2 arguments - a json file as
        input (do not change the input else the file is not recognized any
        more) and one output file (that executable needs to generate)
        (if your code does not take json as input you can for example parse
        json in bash using jq)
        """
        return self.__executable

    @property
    def filetype(self):
        """ (string) : file extension of the output files """
        return self.__filetype

    @directory.setter
    def directory(self, directory) :
        self.__directory = directory
        os.makedirs( self.__directory, exist_ok=True)

    @executable.setter
    def executable(self, executable) :
        self.__executable = executable

    @filetype.setter
    def filetype(self, filetype) :
        self.__filetype = filetype

    def create( self, js):
        """Run a simulation if it does not exist yet

        Using subprocess.run( [executable, in.json, out])
        For this function to work the executable given in the constructor is run.
        This function raises a subprocess.CalledProcessError error
        if the executable returns a non-zero exit code

        Parameters:
        js (dict): the complete input file as a python dictionary. All keys
        must be strings such that js can be converted to JSON.

        Warning:  in order to generate a unique identifier
        js needs to be normalized in the sense that the datatype must match
        the required datatype documented (e.g. 10 in a field requiring float
        is interpreted as an integer and thus produces a different hash)

        Returns:
        string: filename of new entry if it did not exist before
                existing filename else

        """
        ncfile = self.outfile( js)
        exists = os.path.isfile( ncfile)
        if exists:
            return ncfile
        else :
            print( "Running simulation ... ")
            #First write the json file into the database
            # so that the program can read it as input
            with open( self.jsonfile(js), 'w') as f:
                inputstring = json.dumps( js, sort_keys=True, ensure_ascii=True)
                f.write( inputstring)
            #Run the code to create output file
            try :
                subprocess.run( [self.__executable, self.jsonfile(js), ncfile],
                        check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                #clean up entry and escalate exception
                os.remove( ncfile)
                os.remove( self.jsonfile(js))
                raise e
            print( " ... Done")

            return ncfile

    def select( self, js) :
        """ Select an output file based on its input parameters

        This functiont raises a ValueError exception if the file does not exist
        (and thus can be used as an existence check)
        Parameters:
        js (dict): the complete input file as a python dictionary. All keys
        must be strings such that js can be converted to JSON.

        Warning:  in order to generate a unique identifier
        js needs to be normalized in the sense that the datatype must match
        the required datatype documented (e.g. 10 in a field requiring float
        is interpreted as an integer and thus produces a different hash)

        Returns:
        string: filename of existing file
        """
        ncfile = self.outfile( js)
        exists = os.path.isfile( ncfile)
        if not exists:
            raise ValueError( 'Entry does not exist')
        else :
            return ncfile

    def files(self):
        """ Return a list of ids and files existing in directory

        The purpose here is to give the user and iterable object to search
        or tabularize the content of outputfiles
        Returns:
        list of dict : [ {"id": id, "inputfile":jsonfile,
            "outputfile" : outfile}]
        """

        table = []
        for filename in os.listdir(self.__directory) :
            if filename.endswith(".json") and not filename.endswith( "out.json") :
                with open( os.path.join( self.__directory, filename), 'r') as f:
                    #load all json files and check if they are named correctly
                    # and have a corresponding output file
                    js = json.load( f)
                    ncfile = self.outfile( js)
                    exists = os.path.isfile( ncfile)
                    entry = {}
                    if exists : # only add key if the output actually exists
                        entry["id"] = os.path.splitext( os.path.split(filename)[1])[0]
                        entry["inputfile"] = self.jsonfile(js)
                        entry["outputfile"] = ncfile
                        table.append(entry)
        return table

    def table(self):
        """ Return all exisiting (input)-data in a list of python dicts

        Use json.dumps(table(), indent=4) to pretty print
        Note that this list of dictionaries is searchable/ iteratable with standard
        python methods.

        Returns:
        list of dict : [ { ...}, {...},...] where ... represents the actual
            content of the inputfiles
        """
        files = self.files()
        table=[]
        for d in files :
            with open( d["inputfile"]) as f :
                js = json.load( f)
                table.append( js)
        return table

    def hashinput( self, js):
        """Hash the input dictionary

        Params:
        js (dict): the complete input file as a python dictionary. All keys
        must be strings such that js can be converted to JSON.

        Warning:  in order to generate a unique identifier
        js needs to be normalized in the sense that the datatype must match
        the required datatype documented (e.g. 10 in a field requiring float
        is interpreted as an integer and thus produces a different hash)

        Returns:
        string: The hexadecimal sha1 hashid of the input dictionary
        """
        inputstring = json.dumps( js, sort_keys=True, ensure_ascii=True)
        hashed = hashlib.sha1( inputstring.encode( 'utf-8') ).hexdigest()
        return hashed

    def jsonfile( self, js) :
        """ File path to json file from the input

        Does not check if the file actually exists
        Returns:
        path: the file path of the input file
        """
        hashid = self.hashinput(js)
        return os.path.join(self.__directory, hashid+'.json')

    def outfile( self, js) :
        """ File path to output file from the input

        Does not check if the file actually exists
        Returns:
        path: the file path of the output file
        """
        hashid = self.hashinput(js)
        if "json" == self.__filetype :
            return os.path.join( self.__directory, hashid+'_out.json')
        return os.path.join(self.__directory, hashid+'.'+self.__filetype)

    def delete( self, js) :
        """ Delete an entry if it exists """
        ncfile = self.outfile( js)
        exists = os.path.isfile( ncfile)
        if exists :
            os.remove( ncfile)
            os.remove( self.jsonfile(js))

    def replace( self, js) :
        """ Force a re-simulation: delete(js) followed by create(js) """
        self.delete(js)
        return self.create(js)


    def delete_all (self) :
        """ Delete all file pairs id'd by the files method

        and the directory itself (if empty) """
        files = self.files()
        for entry in files :
            os.remove( entry["inputfile"])
            os.remove( entry["outputfile"])
        try :
            os.rmdir( self.__directory)
        except OSError as e:
            pass # if the directory is non-empty nothing happens

#### Idea on submit file creation
# - maybe use the simple-slurm package to generate slurm scripts

#### Ideas on a file view class
# - We can have a separate class managing a view of (input.json, outfile) pairs
#   without creating files but just managing the inputs
# - problem is that inputfiles are seldom separately stored but we would rather
#   need a view of netcdf files where we can assume the input is stored inside
# - no functionality to create or delete files
# - add single files or whole folders (assuming json and nc file has the name)
