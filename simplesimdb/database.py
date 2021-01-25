"""A python module for creation and management of simple simulation data"""
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
    be the program itself or a script calling it. The idea is to let the user define
    how the code should be run.
    """

    __path = './data'
    __out='nc'
    __executable='execute.sh'
    def __init__ (self, directory = './data', outfiletype='nc', executable="./execute.sh"):
        """ init the Manager class

        Parameters
        directory (string) : the path of the folder this class manages.
            Folder is created if it does not exist yet. The class will recognize
            existing files that were generated by a previous session.
        outfiletype (string) : file extension of the output files
        executable (string) : The bash executable to execute in order to
        generate the data
        This file will be called using subprocess.run([executable, id.json,
        id.outfiletype],...) that is it must take 2 arguments - a json file as
        input (do not change the input else the file is not recognized any
        more) and one output file (that executable needs to generate)
        (if your code does not take json as input you can for example parse
        json in bash using jq)
        """
        self.__path = directory
        os.makedirs( directory, exist_ok=True)
        self.__out = outfiletype

        self.__executable = executable


    def create( self, js):
        """Run a simulation if it does not exist yet

        Using subprocess.run( [executable, in.json, out])
        For this function to work the executable given in the constructor is run.
        This function raises a subprocess.CalledProcessError error
        if the executable returns a non-zero exit code

        Parameters:
        js (dict): the complete input file to the simulation
                   see also hashinput

        Returns:
        string: filename of new entry if it did not exist before
                existing filename else

       """
        hashed = self.hashinput(js)
        ncfile = self.outfile( hashed)
        exists = os.path.isfile( ncfile)
        if exists:
            return ncfile
        else :
            print( "Running simulation ... ")
            #First write the json file into the database
            # so that the program can read it as input
            with open( self.jsonfile(hashed), 'w') as f:
                inputstring = json.dumps( js, sort_keys=True, ensure_ascii=True)
                f.write( inputstring)
            #Run the code to create netcdf file
            try :
                subprocess.run( [self.__executable, self.jsonfile(hashed), ncfile],
                        check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                #clean up entry and escalate exception
                os.remove( ncfile)
                os.remove( self.jsonfile(hashed))
                raise e
            print( " ... Done")

            return ncfile

    def select( self, js) :
        """ Select an output file based on its input parameters

        This functiont raises a ValueError exception if the file does not exist
        (and thus can be used as an existence check)
        Parameters:
        js (dict) : The complete input file to the simulation
                    see also hashinput

        Returns:
        string: filename of existing file
        """
        hashed = hashinput(js)
        ncfile = self.outfile( hashed)
        exists = os.path.isfile( ncfile)
        if not exists:
            raise ValueError( 'Entry does not exist')
        else :
            return ncfile

    def table(self):
        """ Return all exisiting (input)-data in a python dict

        Use json.dumps(table(), indent=4) to pretty print
        Note that this dictionary is searchable/ iteratable with standard
        python methods. This table will include both data created by this
        instance of the class as well as previous instances of the class
        working on the same directory

        Returns:
        dict: {id : inputfile}
        """
        table = {}
        for filename in os.listdir(self.__path) :
            if filename.endswith(".json") :
                with open( os.path.join( self.__path, filename), 'r') as f:
                    js = json.load( f)
                    hashed = self.hashinput(js)
                    ncfile = self.outfile( hashed)
                    exists = os.path.isfile( ncfile)
                    if exists : # only add key if the output actually exists
                        table[os.path.splitext( os.path.split(filename)[1])[0]] = js
                    # the key is the hash value
        return table

    def hashinput( self, js):
        """Hash the input file

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

    def jsonfile( self, hashid) :
        """ Create the file path to json file from the hash id """
        return os.path.join(self.__path, hashid+'.json')

    def outfile( self, hashid) :
        """ Create the file path to netcdf file from the hash id """
        if "json" == self.__out :
            return os.path.join( self.__path, hashid+'_out.json')
        return os.path.join(self.__path, hashid+'.'+self.__out)

    def delete( self, js) :
        """ Delete an entry if it exists """
        hashed = self.hashinput(js)
        ncfile = self.outfile( hashed)
        exists = os.path.isfile( ncfile)
        if exists :
            os.remove( ncfile)
            os.remove( self.jsonfile(hashed))

    def replace( self, js) :
        """ Force a re-simulation: delete(js) followed by create(js) """
        self.delete(js)
        return self.create(js)


    def delete_all (self) :
        """ Delete all data displayed by the table method """
        tab = self.table()
        for key in tab :
            print( key)
            self.delete( tab[key])
