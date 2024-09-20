"""Creation and management of simple simulation data"""

import hashlib  # for the hashing
import json
import operator
import os.path  # to check for files
import subprocess  # to run the create program
from contextlib import suppress
from importlib.metadata import PackageNotFoundError, version
from os import PathLike as os_PathLike
from typing import Any, TypeAlias

with suppress(PackageNotFoundError):
    __version__ = version(__package__)


PathLike: TypeAlias = os_PathLike | str
JSONDict: TypeAlias = dict[str, Any]


class Repeater:
    """Manage a single file pair (inputfile, outputfile)

    The purpose of this class is to provide a simple tool when you do not want
    to actually store simulation data on disc (except temporarily). It is
    sometimes more efficient to simply write the data into a single file
    and then reuse/overwrite it in all subsequent simulations.

    """

    def __init__(
        self, executable="./execute.sh", inputfile="temp.json", outputfile="temp.nc"
    ):
        """Set the executable and files to use in the run method"""
        self.executable = executable
        self.inputfile = inputfile
        self.outputfile = outputfile

    @property
    def executable(self):
        return self.__executable

    @property
    def inputfile(self):
        return self.__inputfile

    @property
    def outputfile(self):
        return self.__outputfile

    @executable.setter
    def executable(self, executable):
        self.__executable = executable

    @inputfile.setter
    def inputfile(self, inputfile):
        self.__inputfile = inputfile

    @outputfile.setter
    def outputfile(self, outputfile):
        self.__outputfile = outputfile

    def run(self, js: JSONDict, error: str = "display", stdout: str = "ignore"):
        """Write inputfile and then run a simulation

        Parameters
        ----------
        js:
            the complete input file as a python dictionary. All keys
            must be strings such that js can be converted to JSON.
        error:
            - "raise": raise a subprocess.CalledProcessError error
              if the executable returns a non-zero exit code
            - "display": print(stderr ) then return
            - "ignore" return
        stdout:
            - "ignore" throw away std output
            - "display" print( process.stdout)

        """
        with open(self.inputfile, "w") as f:
            json.dump(js, f, sort_keys=True, ensure_ascii=True, indent=4)
        try:
            process = subprocess.run(
                [self.__executable, self.__inputfile, self.__outputfile],
                check=True,
                capture_output=True,
            )
            if stdout == "display":
                print(process.stdout)
        except subprocess.CalledProcessError as e:
            if error == "display":
                print(e.stderr)
            elif error == "raise":
                raise e

    def clean(self):
        """Remove inputfile and outputfile"""
        if os.path.isfile(self.__inputfile):
            os.remove(self.__inputfile)
        if os.path.isfile(self.__outputfile):
            os.remove(self.__outputfile)


class Manager:
    """Lightweight Simulation Database Manager

    Create, access and display simulation data of a given code as pairs
    ``(inputfile.json : outputfile [, restarted_01, restarted_02, ...])``,
    where all input is given by python dictionaries (stored as json files)
    and the output files (of arbitrary type) are generated by an executable
    that takes the json file as input. This executable is provided by the user.

    .. note:: an executable may only take one sinlge input file and
        may only generate one single output file (except for RESTART,
        see below)

    .. note:: the executable can be a bash script. For example if the
        actual program does not take json input files you could write
        a converter and let the bash script chain the two
        programs. There are endless possibilities.

    Restart Addon (ignore if not used)
    ----------------------------------
    Sometimes simulation outputs cannot be created in a single
    run (due to file size, time limitations, etc.) but rather a simulation is
    partitioned (in time) into a sequential number of separate smaller runs.
    Correspondingly each run sequentially generates and stores only a partition
    of the entire output file. Each run restarts the simulation with the result
    of the previous run. The Manager solves this problem via the
    simulation number n in its member functions. For n>0 create will pass the
    result of the previous simulation as a third input to the executable

    Naming Scheme
    -------------
    By default the naming of the inputs and outputs is based on the sha1 of the
    python dictionary as a sorted string. The user can override this behaviour by
    giving a human readable name in the create function or register one manually.
    This name is then mapped to the sha1 and stored in the file "simplesimdb.json"
    in the data directory. All subsequent references to the input file then map to
    the correct name.

    """

    def __init__(
        self,
        directory: PathLike = "./data",
        filetype: str = "nc",
        executable: str = "./execute.sh",
    ):
        """Init the Manager class

        Restart Addon (ignore if not used)
        ----------------------------------
        If you intend to use the restart option (by passing a simulation number
        ``n > 0`` to create), executable is called with:

        .. code::

            subprocess.run(
                [executable, directory/hashid.json, directory/hashid0xN.filetype, directory/hashid0x(N-1).filetype],
            ...)

        that is it must take a third argument (the previous simulation)

        Parameters
        ----------
        directory:
            the path of the folder this class manages.
            Folder is created if it does not exist yet.  The class will
            recognize existing files that were generated by a previous session.
        filetype:
            file extension of the output files
        executable:
            The executable that generates the data.
            executable is called using subprocess.run([executable,
            directory/hashid.json, directory/hashid.filetype],...) with 2 arguments
            - a json file as input (do not change the input else the file is not
            recognized any more) and one output file (that executable needs to
            generate) (if your code does not take json as input you can for example
            parse json in bash using jq)

        """
        self.directory = directory
        os.makedirs(self.__directory, exist_ok=True)
        self.filetype = filetype
        self.executable = executable

    @property
    def directory(self) -> PathLike:
        """Data directory

        If the directory does not exist it will be created
        """
        return self.__directory

    @property
    def executable(self) -> str:
        """The executable that generates the data.

        The create method calls subprocess.run([executable,
        directory/hashid.json, directory/hashid.filetype],...) that is it must
        take 2 arguments - a json file as input (do not change the input else
        the file is not recognized any more) and one output file (that
        executable needs to generate) (if your code does not take json as input
        you can for example parse json in bash using jq)

        Restart Addon (ignore if not used)
        ----------------------------------
        If you intend to use the restart option (by passing a simulation number
        n>0 to create), the executable is called with
        subprocess.run([executable, directory/hashid.json,
        directory/hashid0xN.filetype, directory/hashid0x(N-1).filetype],...)
        that is it must take a third argument (the previous simulation)
        """
        return self.__executable

    @property
    def filetype(self) -> str:
        """File extension of the output files"""
        return self.__filetype

    @directory.setter
    def directory(self, directory: PathLike):
        self.__directory = directory
        os.makedirs(self.__directory, exist_ok=True)

    @executable.setter
    def executable(self, executable: str):
        self.__executable = executable

    @filetype.setter
    def filetype(self, filetype: str):
        self.__filetype = filetype

    def create(
        self,
        js: JSONDict,
        n: int = 0,
        name: str = "",
        error: str = "raise",
        stdout: str = "ignore",
    ) -> str:
        """Run a simulation if outfile does not exist yet

        Create (write) the in.json file to disc
        Use subprocess.run( [executable, in.json, out])
        If the executable returns a non-zero exit code the inputfile (if n!= 0)
        and outputfile are removed

        .. attention::
            in order to generate a unique identifier
            js needs to be normalized in the sense that the datatype must match
            the required datatype documented (e.g. don't write 10 in a field
            requiring float but 10.0, otherwise it is interpreted as an integer and
            thus produces a different hash)

        Parameters
        ----------
        js:
            the complete input file as a python dictionary. All keys
            must be strings such that js can be converted to JSON.
        n :
            (RESTART ADDON) the number of the simulation
            beginning with 0.  If n>0, we will use the previous simulation as a
            third argument subprocess.run( [executable, in.json, out_n, out_(n-1)])
            This can be used to restart simulations
        name :
            [OPTIONAL] human readable name/id that is used in the
            naming of all files associated with js.
            For example the input is called '<name>.json'.
            If empty, the simplesimdb.json file will be searched for a name,
            afterwards the default sha based naming scheme will be used,
            for example '<sha1>.json'.
            Once a name is given it can only be changed by deleting and
            resimulating the output. Exceptions will be raised on name clashes.
            Names will be stored and mapped to their sha1 in the file
            "simplesimdb.json"
            See also: register
        error :
            - "raise": raise a subprocess.CalledProcessError error if
              the executable returns a non-zero exit code
            - "display": print(stderr ) then return
            - "ignore": return
        stdout :
            - "ignore": throw away std output
            - "display": ``print( process.stdout)``

        Return
        ------
        str:
            filename of new entry if it did not exist before
            existing filename else

        """
        hashid = self.hashinput(js)
        if name != "":
            self.register(js, name)
        ncfile = self.outfile(js, n)
        exists = os.path.isfile(ncfile)
        if exists:
            print("Existing simulation " + hashid[0:6] + "..." + ncfile[-9:])
            return ncfile
        else:
            print("Running simulation " + hashid[0:6] + "..." + ncfile[-9:])
            # First write the json file into the database
            # so that the program can read it as input
            if not os.path.isfile(self.jsonfile(js)):
                with open(self.jsonfile(js), "w") as f:
                    json.dump(js, f, sort_keys=True, ensure_ascii=True, indent=4)
            # Run the code to create output file
            try:
                # Check if the simulation is a restart
                if n == 0:
                    process = subprocess.run(
                        [self.__executable, self.jsonfile(js), ncfile],
                        check=True,
                        capture_output=True,
                    )
                    if stdout == "display":
                        print(process.stdout)
                else:
                    previous_ncfile = self.outfile(js, n - 1)
                    process = subprocess.run(
                        [self.__executable, self.jsonfile(js), ncfile, previous_ncfile],
                        check=True,
                        capture_output=True,
                    )
                    if stdout == "display":
                        print(process.stdout)
            except subprocess.CalledProcessError as e:
                # clean up entry and escalate exception
                if os.path.isfile(ncfile):
                    os.remove(ncfile)
                if n == 0:  # only remove input if not restarted
                    os.remove(self.jsonfile(js))
                if error == "display":
                    print(e.stderr)
                elif error == "raise":
                    raise e

            return ncfile

    def recreate(
        self,
        js: JSONDict,
        n: int = 0,
        name: str = "",
        error: str = "raise",
        stdout: str = "ignore",
    ) -> str:
        """Force a re-simulation: `delete` followed by `create`"""
        self.delete(js, n)
        return self.create(js, n, name, error, stdout)

    def select(self, js: JSONDict, n: int = 0) -> str:
        """Select an output file based on its input parameters

        Raise a ValueError exception if the file does not exist
        else it just returns self.outfile( js, n)

        .. warning::
            in order to generate a unique identifier
            js needs to be normalized in the sense that the datatype must match
            the required datatype documented (e.g. 10 in a field requiring float
            is interpreted as an integer and thus produces a different hash)

        Parameters
        ----------
        js:
            the complete input file as a python dictionary. All keys
            must be strings such that js can be converted to JSON.
        n:
            (RESTART ADDON) the number of the simulation to select
            beginning with 0.

        Returns
        -------
        str:
            self.outfile( js, n) if file exists

        """
        ncfile = self.outfile(js, n)
        exists = os.path.isfile(ncfile)
        if not exists:
            raise ValueError("Entry does not exist")
        else:
            return ncfile

    def count(self, js: JSONDict) -> int:
        """(RESTART ADDON) Count number of output files for given input

        Count the output files associated with the given input parameters that
        currently exist in directory
        (i.e. count n as long as self.exists( js, n) returns True).

        Parameters
        ----------
        js:
            the complete input file as a python dictionary. All keys
            must be strings such that js can be converted to JSON.

        Returns
        -------
        int:
            Number of simulations

        """
        number = 0
        while self.exists(js, number):
            number += 1

        return number

    def exists(self, js: JSONDict, n: int = 0) -> bool:
        """Check for existence of data

        Parameters
        ----------
        js:
            the complete input file as a python dictionary. All keys
            must be strings such that js can be converted to JSON.
        n :
            (RESTART ADDON) the number of the simulation to select
            beginning with 0.

        Returns
        -------
        bool:
            True if output data corresponding to js exists, False else

        """
        ncfile = self.outfile(js, n)
        return os.path.isfile(ncfile)

    def files(self) -> list[dict]:
        """Return a list of dictionaries (sorted by id and number)
        with ids and files existing in directory.

        The purpose here is to give the user an iterable object to search
        or tabularize the content of outputfiles

        Returns
        -------
        list of dict :
            ``[ {"id": id, "n", n, "inputfile":jsonfile, "outputfile"
            : outfile}]``, sorted by 'id' and 'n'

        """
        table = []
        for filename in os.listdir(self.__directory):
            if filename.endswith(".json") and not filename.endswith("out.json"):
                with open(os.path.join(self.__directory, filename)) as f:
                    # load all json files and check if they are named correctly
                    # and have a corresponding output file
                    js = json.load(f)
                    number = self.count(js)  # count how many exist
                    for n in range(0, number):
                        ncfile = self.outfile(js, n)
                        registry = self.get_registry()
                        entry = {
                            "id": registry.get(self.hashinput(js), self.hashinput(js)),
                            "n": n,
                            "inputfile": self.jsonfile(js),
                            "outputfile": ncfile,
                        }
                        table.append(entry)
        return sorted(table, key=operator.itemgetter("id", "n"))

    def table(self) -> list[dict]:
        """Return all exisiting (input)-data in a list of python dicts

        Use ``json.dumps(table(), indent=4)`` to pretty print
        Note that this list of dictionaries is searchable/ iteratable with standard
        python methods.
        RESTART ADDON: the input file for a restarted simulation shows only
        once

        Returns
        -------
        list of dict :
            [ { ...}, {...},...] where ... represents the actual
            content of the inputfiles

        """
        files = self.files()
        table = []
        for d in files:
            with open(d["inputfile"]) as f:
                js = json.load(f)
                if d["n"] == 0:
                    table.append(js)
        return table

    def hashinput(self, js: JSONDict) -> str:
        """Hash the input dictionary

        .. warning::
            in order to generate a unique identifier, ``js`` needs to be
            normalized in the sense that the datatype must match the
            required datatype documented (e.g. 10 in a field requiring
            float is interpreted as an integer and thus produces a
            different hash)

        Parameters
        ----------
        js:
            the complete input file as a python dictionary. All keys
            must be strings such that js can be converted to JSON.

        Returns
        -------
        str:
            The hexadecimal sha1 hashid of the input dictionary

        """
        inputstring = json.dumps(js, sort_keys=True, ensure_ascii=True)
        hashed = hashlib.sha1(inputstring.encode("utf-8")).hexdigest()
        return hashed

    def jsonfile(self, js: JSONDict) -> PathLike:
        """File path to json file from the input

        Does not check if the file actually exists

        Parameters
        ----------
        js:
            the complete input file as a python dictionary. All keys
            must be strings such that js can be converted to JSON.

        Returns
        -------
        str:
            the file path of the input file

        """
        registry = self.get_registry()
        hashid = self.hashinput(js)
        name = hashid
        if hashid in registry:
            name = registry[hashid]
        return os.path.join(self.__directory, name + ".json")

    def outfile(self, js: JSONDict, n: int = 0) -> PathLike:
        """File path to output file from the input

        Do not check if the file actually exists

        Parameters
        ----------
        js:
            the complete input file as a python dictionary. All keys
            must be strings such that js can be converted to JSON.
        n:
            (RESTART ADDON) the number of the simulation to select
            beginning with 0.

        Returns
        -------
        str:
            the file path of the output file

        """
        hashid = self.hashinput(js)
        sim_num = ""
        if n > 0:
            sim_num = hex(n)
        registry = self.get_registry()
        name = hashid
        if hashid in registry:
            name = registry[hashid]
        if self.__filetype == "json":
            return os.path.join(self.__directory, name + sim_num + "_out.json")
        return os.path.join(self.__directory, name + sim_num + "." + self.__filetype)

    def register(self, js: JSONDict, name: str):
        """Register a human readable name for the given input dictionary

        The registry is stored in the file "simplesimdb.json"
        If the given dictionary already has a name associated to it the name is
        already in use or the input file exists under a different name an
        Exception will be raised

        Parameters
        ----------
        js:
            the complete input file as a python dictionary. All keys
            must be strings such that js can be converted to JSON.
        name:
            A human readable name/id that is henceforth used in the
            naming of all files associated with js.

        """
        registry = self.get_registry()
        hashid = self.hashinput(js)
        if name == "simplesimdb":
            raise Exception(
                "The name simplesimdb is not allowed. Choose a different name!"
            )
        if hashid in registry:
            if name != registry[hashid]:
                raise Exception(
                    "The name '"
                    + name
                    + "' cannot be used! The\
 input file is already known under the name '"
                    + registry[hashid]
                    + "'. Use\
 delete to clear the registry."
                )
        else:
            jsonfile = os.path.join(self.__directory, hashid + ".json")
            if os.path.isfile(jsonfile):
                raise Exception(
                    "The name '"
                    + name
                    + "' cannot be used! The\
 input file is already known under the name '"
                    + jsonfile
                    + "'. Use\
 delete to clear the registry."
                )

            registry[hashid] = name
        for key, value in registry.items():
            if (value == name) and key != hashid:
                raise Exception(
                    "The name '"
                    + name
                    + "' is already in use\
 for a different simulation. Choose a different name!"
                )

        self.set_registry(registry)

    def get_registry(self) -> dict[str, str]:
        """Get a dictionary containing the mapping from sha to names

        Read the file "simplesimdb.json"

        Returns
        -------
        dict:
            may be empty, contains all registered names

        """
        registryFile = os.path.join(self.__directory, "simplesimdb.json")
        registry = {}
        if os.path.isfile(registryFile):
            with open(registryFile) as f:
                registry = json.load(f)
        return registry

    def set_registry(self, registry: dict[str, str]):
        """Set the registry with a dictionary containing mapping from sha to names

        .. warning::
            Use with care as this operation can corrupt your naming scheme!

        Parameters
        ----------
        registry:
            if empty, the registry is deleted

        """
        registryFile = os.path.join(self.__directory, "simplesimdb.json")
        with open(registryFile, "w") as f:
            json.dump(registry, f, sort_keys=True, ensure_ascii=True, indent=4)
        if not registry:
            os.remove(registryFile)

    def delete(self, js: JSONDict, n: int = 0):
        """Delete an entry if it exists

        Parameters
        ----------
        js:
            the complete input file as a python dictionary. All keys
            must be strings such that js can be converted to JSON.
        n:
            (RESTART ADDON) the number of the simulation to select
            beginning with 0.

            - In case n>0, only the outputfile outfile(js,n) will be removed.
            - In case n==0, both the outfile as well as the jsonfile(js) and
              any eventual registered names will be removed

        """
        ncfile = self.outfile(js, n)
        exists = os.path.isfile(ncfile)
        if exists:
            os.remove(ncfile)
            if n == 0:
                os.remove(self.jsonfile(js))
                registry = self.get_registry()
                hashid = self.hashinput(js)
                if hashid in registry:
                    del registry[hashid]
                self.set_registry(registry)

    def delete_all(self):
        """Delete all file pairs id'd by the files method

        and the directory itself (if empty)

        .. attention::
            if you want to continue to use the object afterwards
            remember to reset the directory: ``m.directory = '...'``
        """
        files = self.files()
        for entry in files:
            if entry["n"] == 0:
                os.remove(entry["inputfile"])
            os.remove(entry["outputfile"])
        registry = {}
        self.set_registry(registry)
        with suppress(OSError):
            os.rmdir(self.__directory)


# Ideas on a file view class
# - for projects that are not managed or created with simplesimdb
# - We can have a class managing a view of (input.json, outfile) pairs
#   without creating files but just managing the inputs
# - problem is that inputfiles are seldom separately stored but we would rather
#   need a view of netcdf files where we can assume the input is stored inside
# - no functionality to create or delete files
# - add single files or whole folders (assuming json and nc file has the name)
