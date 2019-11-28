import config_file_reader
import router
import sys
if __name__ == '__main__':
    input_file_name = sys.argv[1]
    file_list = config_file_reader.get_file_info(input_file_name)
    if(file_list != False):
        router_id = file_list[0]
        input_ports = file_list[1]
        outputs = file_list[2]
        new_router = router.Router(router_id,input_ports,outputs)
        print("++++++++++++++++++++++++++++++")
        print("Welcome to RIP version2.")
        print("++++++++++++++++++++++++++++++")
        new_router.switch_on_router()