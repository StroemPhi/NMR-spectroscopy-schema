from NMRspec import *
from Provenance import *
from linkml_runtime.dumpers import yaml_dumper
from linkml_runtime.loaders import yaml_loader
from datetime import date
from jdx import jdx2dict, in_dict
import os
import re

today_str = str(date.today())
debug = False
output_path = "./jdx_files/output/"
input_path = "./jdx_files/input/"
id_default_base_uri = "https://nfdi4chem/sparql/"
id_default_prefix = "nmrSPARQL:"


def check_id(source_id, target_id, base_uri=id_default_base_uri) -> str:
    """
    A Function to check if an instance of a schema class has been assigned a target_id.
    If only the default target_id (as specified in the schema) is present,
    its base_uri will be replaced with the source_id.

        @param source_id               the id of a NMR spectroscopy dataset
        @param target_id               the NMRspec schema data class to check/replace the id in
        @param base_uri                the namespace of the dummy id
    """
    if id_default_base_uri in target_id:
        target_id = target_id.replace(id_default_base_uri, f"{source_id}/")
    elif id_default_prefix in target_id:
        target_id = target_id.replace(id_default_prefix, f"{source_id}/")
    return target_id


def load_dataset_metadata(dir_name) -> NmrSpecRecordCollection:
    """
    Function to load the manually curated YAML containing the metadata of the dataset that is being parsed.
    TODO: implement this in a framework where this metadata is automatically generated by some other code
    """
    source = f"{dir_name}/dataset_info.yaml"
    nmr_record_collection = yaml_loader.loads(source=source, target_class=NmrSpecRecordCollection)
    if debug is True:
        print(f"-----\nloaded dataset_info:\n\n{yaml_dumper.dumps(nmr_record_collection)}")
    return nmr_record_collection


def get_record_provenance(nmr_dataset, jdx_dict) -> NmrSpecRecord:
    """get the provenance data of the right NMR record from the YAML by matching the filename of the jdx file
        to the filename provided in under "source" in a record of the YAML """
    for nmr_record in nmr_dataset['contains_assay_records']:
        nmr_record['id'] = check_id(nmr_dataset['id'], nmr_record['id'])
        if os.path.basename(jdx_dict['filename']) in nmr_record['source']:
            return nmr_record


def get_sample(nmr_dataset) -> NmrSample:
    """A function to get the sample metadata from the metadata of a spectroscopy record collection."""
    nmr_sample = nmr_dataset['assays_sample']
    nmr_sample['id'] = check_id(nmr_dataset['id'], nmr_sample['id'])
    if debug is True:
        print(f"------\nsample:\n{nmr_sample}")
    return nmr_sample


def get_assay_data(jdx_dict, nmr_record) -> PulsedNmrAssay:
    """The main function with which to parse a JCAMP-DX file according to the NMR schema and output a YAML"""

    def get_solvent() -> NmrSolvent:
        """A function to get the detail infos on the solvent bases on looking up the value provided in the JCAMP-DX file
        in the dictionary "nmrSolvents" defined here. As the value in the .jdx could be a synonym of the name,
        we need to include synonyms as a list of possible names in this dictionary"""
        nmr_solvents = [
            {"name": ["chloroform-d", "CDCl3", "methanol-d4", "CD3OD", "deuterated chloroform"],
             "id": "CHEBI:85365",
             "smiles": "[2H]C(Cl)(Cl)Cl",
             "iupac_name": "trichloro(deuterio)methane",
             "inchi": "InChI=1S/CHCl3/c2-1(3)4/h1H/i1D",
             "inchikey": "HEDRZPFGACZZDS-MICDWDOJSA-N"},
            {"name": ["acetone-d6", "Acetone-D6", "CD3COCD3"],
             "id": "CHEBI:78217",
             "smiles": "[2H]C([2H])([2H])C(=O)C([2H])([2H])[2H]",
             "iupac_name": "1,1,1,3,3,3-hexadeuteriopropan-2-one",
             "inchi": "InChI=1S/C3H6O/c1-3(2)4/h1-2H3/i1D3,2D3",
             "inchikey": "CSCPPACGZOOCGX-WFGJKAKNSA-N"},
            {"name": ["dimethyl sulfoxide-d6", "DMSO", "d6-DMSO", "DMSO-d6", "DMSO-D6", "C2H6OS",
                      "Dimethylsulfoxide-D6",
                      "deuterated dmso"],
             "id": "https://pubchem.ncbi.nlm.nih.gov/compound/75151",
             "smiles": "[2H]C([2H])([2H])S(=O)C([2H])([2H])[2H]",
             "iupac_name": "trideuterio(trideuteriomethylsulfinyl)methane",
             "inchi": "InChI=1S/C2H6OS/c1-4(2)3/h1-2H3/i1D3,2D3",
             "inchikey": "IAZDPXIOMUYVGZ-WFGJKAKNSA-N"},
            {"name": ["acetonitrile-d3", "CD3CN"],
             "id": "https://pubchem.ncbi.nlm.nih.gov/compound/123151",
             "smiles": "[2H]C([2H])([2H])C#N"},
            {"name": ["deuterium oxide", "D2O"],
             "id": "https://pubchem.ncbi.nlm.nih.gov/compound/24602",
             "smiles": "[2H]O[2H]"},
            {"name": ["dichloromethane-d2", "CD2Cl2"],
             "id": "https://pubchem.ncbi.nlm.nih.gov/compound/160586", "smiles": "[2H]C([2H])(Cl)Cl"},
            {"name": ["ethanol-d6", "CD3CD2OD"],
             "id": "https://pubchem.ncbi.nlm.nih.gov/compound/102138",
             "smiles": "[2H]C([2H])([2H])C([2H])([2H])O[2H]"},
            {"name": ["methanol-d4", "CD3COD", "MeOD"],
             "id": "https://pubchem.ncbi.nlm.nih.gov/compound/71568",
             "smiles": "[2H]C([2H])([2H])O[2H]"},
            {"name": ["nitrobenzene-d5", "C6D5NO2"],
             "id": "https://pubchem.ncbi.nlm.nih.gov/compound/123210",
             "smiles": "[2H]C1=C(C(=C(C(=C1[2H])[2H])[N+](=O)[O-])[2H])[2H]"},
            {"name": ["nitromethane-d3", "CD3NO2"],
             "id": "https://pubchem.ncbi.nlm.nih.gov/compound/123293",
             "smiles": "[2H]C([2H])([2H])[N+](=O)[O-]",
             "inchikey": "LYGJENNIWJXYER-FIBGUPNXSA-N"},
            {"name": ["pyridine-d5", "C5D5N"],
             "id": "https://pubchem.ncbi.nlm.nih.gov/compound/558519",
             "smiles": "[2H]C1=NC([2H])=C([2H])C([2H])=C1[2H]"},
            {"name": ["toluene-d8", "C6D5CD3"],
             "id": "https://pubchem.ncbi.nlm.nih.gov/compound/74861",
             "smiles": "[2H]C([2H])([2H])C1=C([2H])C([2H])=C([2H])C([2H])=C1[2H]"},
            {"name": ["benzene-d6", "C6D6"],
             "id": "https://pubchem.ncbi.nlm.nih.gov/compound/71601",
             "smiles": "C1([2H])=C([2H])C([2H])=C([2H])C([2H])=C1[2H]"}
        ]
        solvent_name = None
        if '.solvent name' in jdx_dict:
            solvent_name = jdx_dict['.solvent name']
        elif '.solventname' in jdx_dict:
            solvent_name = jdx_dict['.solventname']
        else:
            exit(f"ERROR: no solvent provided in the JCAMP-DX -> {jdx_dict['filename']} cannot be parsed")
        solvent_dict = {}
        for possible_solvent in nmr_solvents:
            for key, value in possible_solvent.items():
                if key == "name":
                    for name in value:
                        if solvent_name.lower() in name.lower():
                            solvent_dict = possible_solvent
                elif value == solvent_name:
                    solvent_dict = possible_solvent
        parsed_solvent = NmrSolvent(id=solvent_dict['id'],
                                    name=solvent_dict['name'][0],
                                    inchi=solvent_dict['inchi'],
                                    inchikey=solvent_dict['inchikey'],
                                    iupac_name=solvent_dict['iupac_name'],
                                    smiles=solvent_dict['smiles'])
        if debug is True:
            print(f"----\nparsed_solvent: {parsed_solvent}")
        return parsed_solvent

    def get_solution() -> NmrSolution:
        nmr_solution = NmrSolution(solvent=get_solvent(), sample=sample)
        nmr_solution['id'] = check_id(nmr_record['id'], nmr_solution['id'])
        return nmr_solution

    def get_manufacturer() -> Manufacturer:
        """
        function to parse the manufacturer  of the use NMR device from the jdx, by looking for its name in any of the
        jdx_dict values.
        TODO:
            make the list a list of dicts by adding websites to each manufacturer as default values, analog to
            nmr_solvents and nmr_pulse_programs
        """
        nmr_manufacturers = ["Acorn NMR Inc", "Agilent Technologies", "Applied Biosystems", "Bruker", "Doty Scientific",
                             "FOSS", "General Electric", "JEOL", "JS Research", "Jasco", "Kimble Chase", "MR Resources",
                             "OceanOptics", "Oxford Instruments", "Perkin Elmer", "Phillips", "Siemens AG",
                             "Spinlock SRL", "TX", "ThermoFinnigan", "ThermoMattson", "ThermoNicolet", "Varian",
                             "Waters", "Wilmad", "acdlabs", "micromass", "tecmag"]
        for possible_manufacturer in nmr_manufacturers:
            if in_dict(jdx_dict, possible_manufacturer):
                manufacturer = Manufacturer(name=possible_manufacturer)
                manufacturer['id'] = check_id(nmr_record['id'], manufacturer['id'])
                return manufacturer
            else:
                manufacturer = Manufacturer()
        manufacturer['id'] = check_id(nmr_record['id'], manufacturer['id'])
        return manufacturer

    def get_spectrometer() -> NmrSpectrometer:
        """
        function to parse the spectrometer data from the jdx file if it is present in there
        """
        if "spectrometer/data system" in jdx_dict:
            nmr_spectrometer = NmrSpectrometer(type=jdx_dict['spectrometer/data system'],
                                               manufactured_by=get_manufacturer())
            nmr_spectrometer['id'] = check_id(nmr_record['id'], nmr_spectrometer['id'])
        else:
            nmr_spectrometer = NmrSpectrometer()
            nmr_spectrometer['id'] = check_id(nmr_record['id'], nmr_spectrometer['id'])
        return nmr_spectrometer

    def get_assay_date() -> str:
        """function to parse the date of the NMR assay from the jdx file"""

        def proper_datetime(datetime_str) -> Datetime:
            """ugly helper function to prune the timezone from a datetime string like '2019/07/18 01:16:26+0000'.
             TODO: check if this is an encoding error of the jdx writing software or if this should be actually
              handled by the linkML code
              ERROR in
                'linkml_runtime/utils/metamodelcore.py", line 277,
                        ValueError: 2019-07-18 01:16:26+0000 is not a valid datetime'
            """

            if '+' in datetime_str:
                datetime = datetime_str.split('+')
                return datetime[0]

        if 'long date' in jdx_dict.keys():
            assay_date = proper_datetime(str(jdx_dict['long date']).replace('/', '-'))
        elif 'longdate' in jdx_dict.keys():
            assay_date = proper_datetime(str(jdx_dict['longdate']).replace('/', '-'))
            jdx_dict['longdate']
        elif 'date' in jdx_dict.keys():
            assay_date = proper_datetime(str(jdx_dict['date']).replace('/', '-'))
            jdx_dict['date']
        if debug is True:
            print(f"----\nassay_date: {assay_date}")
        return assay_date

    def get_acquisition_nuclei() -> list:
        """
        function to parse the aquisition nuclei from the jdx file by looking for three possible jdx fields
            1) get from the '$NUC[1-8]' field, if it exists
            2) get from the '.nucleus' field, if it exists
            3) get it from the '.observe nucleus' field, which should always be there but might not contain all nuclei
        """
        acquisition_nuclei = []
        if '$nuc1' in jdx_dict:
            if jdx_dict['$nuc1'] != '<off>':
                acquisition_nuclei.append(jdx_dict['$nuc1'].replace('<', '').replace('>', ''))
            if jdx_dict['$nuc2'] != '<off>':
                acquisition_nuclei.append(jdx_dict['$nuc2'].replace('<', '').replace('>', ''))
            if jdx_dict['$nuc3'] != '<off>':
                acquisition_nuclei.append(jdx_dict['$nuc3'].replace('<', '').replace('>', ''))
            if jdx_dict['$nuc4'] != '<off>':
                acquisition_nuclei.append(jdx_dict['$nuc4'].replace('<', '').replace('>', ''))
            if jdx_dict['$nuc5'] != '<off>':
                acquisition_nuclei.append(jdx_dict['$nuc5'].replace('<', '').replace('>', ''))
            if jdx_dict['$nuc6'] != '<off>':
                acquisition_nuclei.append(jdx_dict['$nuc6'].replace('<', '').replace('>', ''))
            if jdx_dict['$nuc7'] != '<off>':
                acquisition_nuclei.append(jdx_dict['$nuc7'].replace('<', '').replace('>', ''))
            if jdx_dict['$nuc8'] != '<off>':
                acquisition_nuclei.append(jdx_dict['$nuc8'].replace('<', '').replace('>', ''))
        elif '.nucleus' in jdx_dict:
            nuclei = jdx_dict['.nucleus'].split(',')
            nuclei[1] = nuclei[1].strip()
            acquisition_nuclei.extend(nuclei)
        elif '.observenucleus' in jdx_dict:
            acquisition_nuclei.append(jdx_dict['.observenucleus'].replace('^', ''))
        else:
            acquisition_nuclei.append(jdx_dict['.observe nucleus'].replace('^', ''))
        if debug is True:
            print(f"-----\naquisition nuclei: {acquisition_nuclei}")
        return acquisition_nuclei

    def get_dimension() -> str:
        """Function to parse the dimensionality of the pulsed NMR assay from the jdx file,
        if the key for this is present. If it is missing, it'll default to "1D."""
        if 'numdim' in jdx_dict:
            if debug is True:
                print(f"-----\ndimensionality: {jdx_dict['numdim']}D")
            return f"{jdx_dict['numdim']}D"
        else:
            print("WARNING: no dimensionality statement found in jdx file, thus taking '1D' as default.")
            return "1D"

    def get_observed_frequencies() -> list:
        """function to parse observed frequencies from the jdx file"""
        if '$sfo1' in jdx_dict:
            observed_frequencies = set()
            for n in range(1, 8):
                observed_frequencies.add(jdx_dict[f"$sfo{n}"])
            observed_frequencies = list(observed_frequencies)
        elif '.observefrequency' in jdx_dict:
            observed_frequencies = [jdx_dict['.observefrequency']]
        else:
            observed_frequencies = [jdx_dict['.observe frequency']]
        if debug is True:
            print(f"-----\nobserved frequencies: {observed_frequencies}")
        return observed_frequencies

    def get_pulse_program() -> str:
        """
        Function to parse the pulse sequence form the jdx file by looking up the jdx value in a  controlled list of
        dicts see allowed values in the respective enum of the schema.
        TODO:
            1) document better how this is needed, in order to ground all possible vendor specific pulse programs to a
                certain standard. See also https://github.com/StroemPhi/NMRspec/issues/5
            2) add Bruker codes to get matches for the ones that are not derivable by the 'name' values#
        """
        nmr_pulse_program_cv = [{"name": "NMR", "bruker": "zg", "jeol_h": "proton", "jeol_c": "carbon"},
                                {"name": "Inverse NMR"},
                                {"name": "COSY"},
                                {"name": "SECSY"},
                                {"name": "RELAY"},
                                {"name": "TOCSY"},
                                {"name": "ROESY"},
                                {"name": "NOESY"},
                                {"name": "J_Resolved", "bruker": "jres"},
                                {"name": "DEPT"},
                                {"name": "INEPT"},
                                {"name": "HECTOR"},
                                {"name": "COLOC"},
                                {"name": "HOESY"},
                                {"name": "INADEQUATE"},
                                {"name": "HMQC"},
                                {"name": "DEPT-HMQC"},
                                {"name": "HSQC"},
                                {"name": "Inverse-INEPT"},
                                {"name": "TROSY"},
                                {"name": "CRINEPT"},
                                {"name": "HMQC-COSY"},
                                {"name": "H2BC"},
                                {"name": "HQMC-TOSCY"},
                                {"name": "HMQC-ROESY"},
                                {"name": "HMQC-NOESY"},
                                {"name": "HSQC-TOSCY"},
                                {"name": "HSQC-ROESY"},
                                {"name": "HSQC-NOESY"},
                                {"name": "HMBC"},
                                {"name": "HSQMBC"},
                                {"name": "EXSIDE"},
                                {"name": "HETLOC"},
                                {"name": "HSQC-HECADE"},
                                {"name": "ADEQUATE"},
                                {"name": "DOSY"},
                                {"name": "STE"},
                                {"name": "STEBP"},
                                {"name": "DSTE"},
                                {"name": "DSTEBP"},
                                {"name": "COSY-DOSY"},
                                {"name": "DOSY-TOCSY"},
                                {"name": "DOSY-NOESY"},
                                {"name": "DOSY-HMQC"},
                                {"name": "STD-TOSCY"},
                                {"name": "STD-NOESY"},
                                {"name": "STD-HSQC"},
                                {"name": "CLEANEX"},
                                {"name": "CLEANEX-HSQC"},
                                {"name": "CLEANEX-TROSY"}
                                ]
        # pulse program as stored in jdx
        if '.pulse sequence' or '.pulsesequence' in jdx_dict:
            if '.pulse sequence' in jdx_dict:
                pulse_program_jdx = jdx_dict['.pulse sequence'].lower()
            elif '.pulsesequence' in jdx_dict:
                pulse_program_jdx = jdx_dict['.pulsesequence'].lower()
            else:
                pulse_program_jdx = "N/A"
            pulse_program_parsed = None
            pulse_program_custom = None
            for possible_pulse_program in nmr_pulse_program_cv:
                for key, value in possible_pulse_program.items():
                    # normalize controlled terms to be able to match to manufacturer codes
                    value = value.lower()
                    # split controlled term of combined pulse programs, as the order might be different in Bruker & JEOl
                    # (e.g. DOSY-COSY vs cosy-dosy)
                    if '-' in value:
                        value = value.split('-')
                        # return controlled term if the combined pulse program could be matched
                        if value[0] in pulse_program_jdx and value[1] in pulse_program_jdx:
                            pulse_program_parsed = possible_pulse_program["name"]
                    # return controlled term if there is a pulse program match
                    elif re.match(rf"(^{value})", pulse_program_jdx):
                        pulse_program_parsed = possible_pulse_program["name"]
            # return unknown jdx pulse program code
            if not pulse_program_parsed:
                if '.pulse sequence' in jdx_dict:
                    pulse_program_custom = jdx_dict['.pulse sequence']
                elif '.pulsesequence' in jdx_dict:
                    pulse_program_custom = jdx_dict['.pulsesequence']
                else:
                    pulse_program_custom = pulse_program_jdx
                pulse_program_parsed = "Custom"
        else:
            print("-----\nError: There is no pulse program specified in the jdx file!")
            pulse_program_parsed = "not provided"
        if debug is True:
            print(f"-----\npulse program: {pulse_program_parsed, pulse_program_custom}")
        return pulse_program_parsed, pulse_program_custom

    # parse the pulse program
    pulprog, pulprog_custom = get_pulse_program()

    nmr_assay = PulsedNmrAssay(solution=get_solution(),
                               spectrometer=get_spectrometer(),
                               has_dimension=get_dimension(),
                               pulse_program=pulprog,
                               pulse_program_custom=pulprog_custom,
                               acquisition_nuclei=get_acquisition_nuclei(),
                               assay_date=get_assay_date(),
                               observed_frequencies=get_observed_frequencies())

    nmr_assay['id'] = check_id(nmr_record['id'], nmr_assay['id'])

    if debug is True:
        print(f"-----\nparsed assay metadata:\n\n{yaml_dumper.dumps(nmr_assay)}")
    return nmr_assay


if __name__ == '__main__':

    for root, subdirectories, files in os.walk(input_path):
        for subdirectory in subdirectories:
            directory = f"{os.path.join(root, subdirectory)}/"
            # get the context infos from the provided YAML
            dataset = load_dataset_metadata(directory)
            # print(dataset['description'])
            sample = get_sample(dataset)
            nmr_records = []
            for fname in os.listdir(os.path.join(directory)):
                if fname.endswith('.jdx') or fname.endswith('.dx'):
                    jdx_dict = jdx2dict(f"{directory}{fname}")
                    print(f"-----\nparsing: {fname}")
                    record = get_record_provenance(dataset, jdx_dict)
                    assay = get_assay_data(jdx_dict, record)
                    record['output_of_nmr_assay'] = assay
                    nmr_records.append(record)
            dataset['contains_assay_records'] = nmr_records
            output_file = dataset['name'].replace(' ','_').replace('/','_')
            with open(f"{output_path}{output_file}.yaml", 'w', encoding='utf-8') as f:
                f.write(
                    "# -*- coding: utf-8 -*-\n\n"
                    "#################################################\n"
                    "# a JCAMP-DX dataset parsed to YAML\n" 
                    "# using https://github.com/StroemPhi/NMRspec\n" 
                    f"# created: {today_str}\n" 
                    "#################################################\n\n"
                )
                f.write(yaml_dumper.dumps(dataset))

                print("-----\nAll went according to the plan! And the parsed dataset was saved to:\n"
                      f"{output_path}{output_file}.yaml")
