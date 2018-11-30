"""
Iterate all temporary declaration files and 
make some quick fixes to create some basic 
functionality 
    - remove .js from imports
    - transform @typedef comments to interfaces
    - transform opt_ to optional declaration in constructor
    - misc fixes
"""

import json
import os
import re 

def fix_imports(content):
    all_imports = collect_imports(content)
    for _import in all_imports: 
        content = content.replace(_import, _import.replace(".js'", "'"))
    return content

def no_never_returns(content):
    return content.replace(": never", ": any")

def no_this_returns(content):
    return content.replace(": this", ": any")

def mark_optional(content):
    optional_args = re.findall("opt_[a-zA-Z]*?:", content)
    optional_args = list(set(optional_args))
    for arg in optional_args:
        new_arg = arg.replace("opt_", "").replace(":", "?:")
        if new_arg == "this?:":
            new_arg = "_this?:"
        content = content.replace(arg, new_arg)
    return content

"""
Splits a doc line into 
ts_type ({})
ol_name ([])
description (the rest)
"""
def parse_property_line(doc_line):
    # replacements for special cases 
    doc_line = doc_line.replace("{{https: string}}", "{string}")
    ts_type = re.split("[{}]", doc_line)[1]
    try: 
        ol_name = re.split("[\[\]]", doc_line)[1]
        ol_name = ol_name.split("=")[0].strip()
        description = doc_line.partition("]")[2]
    # in case no brackets provided with source, use first word as olName 
    except:
        # print("EXCEPT")
        # print(doc_line)
        text = doc_line.partition("}")[2].strip()
        ol_name = text.split(" ")[0].strip()
        description = " ".join(text.split(" ")[1:])
    description = re.sub("[\*/]", "", description)
    return {
        "tsType": ts_type, 
        "olName": ol_name, 
        "description": description
    }

def parse_typedef_line(type_line):
    split_line = re.split("[{}]", type_line)
    return {
        "type": split_line[1],
        "name": split_line[2].strip().split(" ")[0]
    }

def translate_type(original_type):
    if original_type in ['string', 'number', 'Array<string>', 'Array<number>']:
        return original_type
    else: 
        return 'any'

"""
Finds all @typedef comments and creates interfaces 
"""
def typedef_to_interface(content):
    interfaces = []
    interface_names = []
    typedefs = re.findall("/\*\*.*?@typedef.*?\*/", content, re.DOTALL)
    for typedef in typedefs:
        # don't parse without property
        if "@property" in typedef:
            typedef_line = re.search("@typedef.*", typedef).group()
            typedef_obj = parse_typedef_line(typedef_line)
            interface_str = """\nexport interface {typeName} {{\n""".format(
                typeName=typedef_obj['name']
            )
            property_lines = typedef.split("@property")
            for prop_line in property_lines[1:]:
                prop_obj = parse_property_line(prop_line)
                if prop_obj['olName'] != '':
                    interface_str += """  /** {description} */\n  {olName}?: {tsType};\n""".format(
                        description=prop_obj["description"],
                        tsType=translate_type(prop_obj["tsType"]),
                        olName=prop_obj["olName"]
                    )
            interface_str += "\n}\n"
            interfaces.append(interface_str)
            interface_names.append(typedef_obj['name'])
    return interfaces, interface_names

def collect_imports(content):
    return re.findall("^import.*?from '.*?';", content, re.MULTILINE)

def add_after_import(content, add_cont):
    imports = collect_imports(content)
    if len(imports):
        last_import = imports[len(imports)-1]
        content = content.replace(last_import, last_import + add_cont)
    else: 
        content = add_cont + content
    return content

def use_typed_options_in_constructor(content, has_own_object, import_object):
    # get the class declaration including constructor
    # and extract the @param declaration
    class_declarations = re.findall("declare class.*?constructor\(.*?\)", content, re.DOTALL)
    for class_declaration in class_declarations:
        try:
            parameter = re.search("@param.*", class_declaration).group()
        except:
            continue
        param_content = re.split("[{}]", parameter)[1]

        # Only apply to options
        if not "constructor(options" in class_declaration:
            continue 

        # If simple options specified, the interface is 
        # present in the declaration itself
        # or exported from the extended class
        optional = param_content.endswith("=")
        if optional:
            param_content = param_content[:-1]
        if param_content.startswith("!"):
            param_content = param_content[1:]
        # resolve import
        if param_content.startswith("import("):
            import_path = param_content.split('"')[1].replace(".js", "")
            import_name = import_path.rpartition("/")[2]
            type_name = param_content.rpartition(".")[2]
            if (type_name == 'default'):
                type_name = import_name
            if optional:
                content = content.replace("constructor(options?: any", "constructor(options?: " + type_name)
            else:
                content = content.replace("constructor(options: any", "constructor(options: " + type_name)            
            new_import = "import {" + type_name + "} from '" + import_path + "';\n"
            imports = collect_imports(content)
            if len(imports):
                content = content.replace(imports[0], imports[0] + "\n" + new_import)
            else:
                content = new_import + "\n" + content
        # no external import (assume same class or extending)
        else:
            # if extending class and no Object type definition in 
            # the class itself, add an import 
            # (for example TileLayer extends BaseTileLayer)
            extends = "extends" in class_declaration
            if extends and not has_own_object:
                declare_statement = re.search("declare class.*", class_declaration).group()
                base_class = declare_statement.split(" ")[4]
                import_statement = "\nimport { Options } from " + import_dict[base_class] + ";"
                imports = collect_imports(content)
                if len(imports):
                    last_import = imports[len(imports)-1]
                    content = content.replace(last_import, last_import + import_statement)
                else: 
                    content = import_statement + "\n" + content

            if optional:
                content = content.replace("constructor(options?: any", "constructor(options?: " + param_content)
            else:
                content = content.replace("constructor(options: any", "constructor(options: " + param_content)
    return content 

def generate_import_dict(content):
    import_dict = {}
    imports = collect_imports(content)
    for _import in imports:
        _import = re.sub("[{}]", "", _import)
        import_parts = _import.split(" ")
        import_dict[import_parts[1]] = import_parts[3].replace(";", "")
    return import_dict

"""
due to renaming opt to ?, duplicate identifiers can occur (e.g. in extent.d.ts)
"""
def fix_duplicate_params(content):
    fun_defs = re.findall("[a-zA-Z]*\([a-zA-Z]*?: [a-zA-Z].*?\)\: [a-zA-Z]*;", content)
    for fun_def in fun_defs:
        fun_split = re.split("[()]", fun_def)
        params_str = fun_split[1]
        params = params_str.split(",")
        param_names = [param.split(":")[0].replace("?", "").strip() for param in params]
        param_increment = {}
        for param_idx, param_name in enumerate(param_names):
            if param_names.count(param_name) > 1:
                if param_name not in param_increment:
                    param_increment[param_name] = 1
                else:
                    param_increment[param_name] += 1
                    # already present, rename original param
                    params[param_idx] = params[param_idx].replace(param_name, param_name + str(param_increment[param_name]))
        new_fun_def = fun_split[0] + "(" + ", ".join(params) + ")" + fun_split[2]
        content = content.replace(fun_def, new_fun_def)
    return content

def resolve_generics(content):
    generics = []
    class_declarations = re.findall("/\*\*.*?@classdesc.*?\*/[ \n]*?declare class [a-zA-Z]* ", content, re.DOTALL)
    for class_declaration in class_declarations:
        if "@template T" in class_declaration:
            print("IS GENERIC")
            last_line = class_declaration.rpartition("\n")[2]
            class_name = last_line.strip().rpartition(" ")[2]
            print(class_name)
            generics.append(class_name)
            content = content.replace(last_line, last_line.strip() + "<T> ")

    return content, generics

TS_BASE = "./@types/ol/"

fw = os.walk(TS_BASE)

# collect all generic classes for a second iteration 
# to add generic typing to extending classes 
generic_classes = []

while True: 
    try:
        curr_dir_info = next(fw)
        for _file in curr_dir_info[2]:
            if _file.endswith("d.ts"):
                ts_path = os.path.join(curr_dir_info[0], _file)
                # Open original js file (no .ts-file) for @typedefs
                js_path = ts_path.replace(".d.ts", ".ts")
                with open(js_path) as fh:
                    js_cont = fh.read()
                with open(ts_path) as fh:
                    cont = fh.read()
                print(ts_path)
                # generate a dictionnary with imports to 
                # path to resolve import paths
                import_dict = generate_import_dict(cont)
                cont = fix_imports(cont)
                cont = mark_optional(cont)
                cont = no_never_returns(cont)
                cont = no_this_returns(cont)
                cont, generics = resolve_generics(cont)
                if len(generics):
                    generic_classes.extend(generics)
                # Problem: typedefs can be cut off during tsc-compilation
                # (-> see View.d.ts and View.js for an example)
                interfaces, interface_names = typedef_to_interface(js_cont)
                cont = add_after_import(cont, "\n".join(interfaces))
                has_own_object = len(interface_names) > 0
                cont = use_typed_options_in_constructor(cont, has_own_object, import_dict)
                cont = fix_duplicate_params(cont)
                with open(ts_path, "w+") as fh_out:
                    fh_out.write(cont)
    except StopIteration:
        break


## Second iteration to check if class extends a generic
fw = os.walk(TS_BASE)
print("Adding generic typing to extending classes")
while True: 
    try:
        curr_dir_info = next(fw)
        for _file in curr_dir_info[2]:
            if _file.endswith("d.ts"):
                ts_path = os.path.join(curr_dir_info[0], _file)
                with open(ts_path) as fh:
                    cont = fh.read()
                rewrite = False
                extending_declarations = re.findall("declare class [a-zA-Z]* extends [a-zA-Z]* ", cont, re.MULTILINE)
                for declaration in extending_declarations:
                    decl_class = declaration.split(" ")[2]
                    base_class = declaration.split(" ")[4]
                    if base_class in generic_classes:
                        print(declaration)
                        new_declaration = declaration.replace(base_class, base_class + "<T>")
                        new_declaration = new_declaration.replace(decl_class, decl_class + "<T>")
                        print(new_declaration)
                        cont = cont.replace(declaration, new_declaration)
                        rewrite = True
                if rewrite:
                    with open(ts_path, "w+") as fh_out:
                        fh_out.write(cont)

    except StopIteration:
        break


## Apply some manual fixes 
print("Applying manual fixes")
with open("manual-fixes.json") as fh:
    fixes = json.load(fh)
for fix in fixes:
    def_file = os.path.join(TS_BASE, fix["file"])
    print(def_file)
    with open(def_file) as fh:
        cont = fh.read()
        cont = cont.replace(fix["original"], fix["replacement"])
    with open(def_file, "w+") as fh_out:
        fh_out.write(cont)
