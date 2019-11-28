import re
def get_file_info(file_name):
    try:
        config_file = open(file_name)
    except:
        print("ERROR: Cannot find the file!")
        return False
    config_file_read = config_file.read()
    config_file_list = config_file_read.splitlines()
    if(len(config_file_list) != 3):
        print("ERROR: Configure file is incomplete!")
        return False
    if("router-id" not in config_file_list[0]):
        print("ERROR: Router ID part is not in the configure file!")
        return False
    if("input-ports" not in config_file_list[1]):
        print("ERROR: input ports part is not in the configure file!")
        return False
    if("outputs" not in config_file_list[2]):
        print("ERROR: Outputs part is not in the configure file!")
        return False
    try:
        router_id = int(config_file_list[0].split()[1])
    except:
        print("ERROR: Router ID is not a integer value!")
        return False
    if(router_id < 1 or router_id > 64000):
        print("ERROR: Router id must between 1 and 64000!")
        return False
    inputs_strings = re.split(' |, ', config_file_list[1])
    input_ports = []
    for inputs_string in inputs_strings[1:]:
        try:
            input_port = int(inputs_string)
        except:
            print("ERROR: Input port is not a integer value!")
            return False
        if(input_port <1024 or input_port > 64000):
            print("ERROR: Input port number must between 1024 and 64000!")
            return False
        elif(input_port in input_ports):
            print("ERROR: Input port number already exists!")
            return False
        else:
            input_ports.append(input_port)
    outputs_strings = re.split(' |, ', config_file_list[2])
    outputs = {}
    for outputs_string in outputs_strings[1:]:
        outputs_info = re.split('-', outputs_string)
        try:
            output_port = int(outputs_info[0])
        except:
            print("ERROR: Onput port is not a integer value!")
            return False
        if(output_port <1024 or output_port > 64000):
            print("ERROR: Output port number must between 1024 and 64000!")
            return False
        for router_id_output in outputs.keys():
            if(output_port == outputs[router_id_output][1]):
                print("ERROR: Output port already exists!")
                return False
        try:
            metric_value = int(outputs_info[1])
        except:
            print("ERROR: metric value is not a integer value!")
            return False
        try:
            output_router_id = int(outputs_info[2])
        except:
            print("ERROR: Output router ID is not a integer value!")
            return False
        if(output_router_id in outputs.keys()):
            print("ERROR: Output router ID is exists!")
            return False
        outputs[output_router_id] = (metric_value, output_port)
    return [router_id, input_ports, outputs]