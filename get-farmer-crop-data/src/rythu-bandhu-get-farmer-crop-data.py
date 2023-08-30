import datetime
import json
import logging
import sys
import urllib.error
from configparser import ConfigParser
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import re
import pika
import xmltodict
from dateutil import parser

config = ConfigParser(interpolation=None)
config.read("./secrets/config.ini")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
time_format = "%Y-%m-%dT%H:%M:%SZ"
time_formatter = "%Y-%m-%dT%H:%M:%S.%f"

class RabbitMqServerConfigure():

    def __init__(self, username, password, host, port, vhost, queue):

        """ Server initialization   """

        self.username = username
        self.password = password
        self.host = host
        self.port = port
        self.vhost = vhost
        self.queue = queue

class rabbitmqServer(object):

    def __init__(self, server):

        """
        Establishing the connection
        :param server: Object of class RabbitMqServerConfigure
        :return:None
        """

        self.server = server 
        
        self.connection = pika.BlockingConnection(
            pika.URLParameters(f'amqps://{self.server.username}:{self.server.password}@{self.server.host}:{self.server.port}/{self.server.vhost}'))

        self.channel = self.connection.channel()
        
        logging.info("......Server started waiting for Messages......")
        
    def startserver(self, on_request):

        """
        Starting the server to consume
        :param on_reuest:callback
        :return:None
        """
        self.channel.basic_qos(prefetch_count=1)

        self.channel.basic_consume(
            queue=self.server.queue,
            on_message_callback=on_request
            )

        self.channel.start_consuming()  
        
        
    def publish(self, payload, rout_key, corr_id, method):

        """
        :param payload: JSON payload
        :param rout_key: reply queue
        :param corr_id: correlation id 
        :return: None
        """

        message = json.dumps(payload)
        
        self.channel.basic_publish(
            exchange='', 
            routing_key=rout_key, 
            properties=pika.BasicProperties(correlation_id = corr_id),
            body=message
            )
                
        self.channel.basic_ack(delivery_tag=method.delivery_tag)

        logging.info(".......Message is published.......")

class get_farmer_data:

    def __init__(self, url, queue, iudx_username, iudx_password):

        """ Variable initialization   """

        self.url = url
        self.queue = queue
        self.iudx_username = iudx_username
        self.iudx_password = iudx_password

    def process_request(self, ch, method, properties, body):

        """
        Processing the request
        :param method: 
        :param properties: properties consists of required ids
        :param body: request json response to form the api
        :return:None
        """

        logging.info(".......RequestJson received......")
        self.json_object = json.loads(body)
        self.rout_key=properties.reply_to
        self.corr_id = properties.correlation_id
        self.method = method
        
        logging.info(".........Forming the api.........")

        self.form_api()

    def form_api(self):
        
        """
        Forming the API
        :return:None
        """
        error_dict = {}
        
        try:
            query=self.json_object["searchType"]
            query_list=query.split("_")

            if "attributeSearch" in query_list:
                attribute_dict = self.attribute_end_dict("attr-query")

            if "temporalSearch" in query_list:
                temporal_dict = self.temporal_end_dict("temporal-query")
            
            if attribute_dict and temporal_dict:
                end_dict = {**attribute_dict, **temporal_dict}

            else:
                end_dict = attribute_dict

            self.getData(end_dict)
            return

        except KeyError as ek:

            logging.error("A Key error occurred: {}".format(ek))

            error_dict["statusCode"] = 400
            error_dict["details"] = f"Keyerror: Key {str(ek)} not found in the json request body"

        except Exception as e:  

            logging.error("An Unknown Error occurred: {}".format(e))

            error_dict["statusCode"] = 400
            error_dict["details"] = str(e)

        server.publish(error_dict, self.rout_key, self.corr_id, self.method) 

    def attribute_end_dict(self, query_type):

        """
        Forming the end point
        :params query_type: attribute query
        :return attribute endpoint: attribute endpoint consists of attribute queries
        """

        attr_list = self.json_object[query_type].split(";")
        attr_dict = {}

        for attr in attr_list: 

            match = re.search(r'[pP][pP][bB][nN][oO][=][=]', attr)
            
            if match!=None:
                attr_dict["PPBNO"] = re.sub(r'[pP][pP][bB][nN][oO][=][=]','',attr)

        return attr_dict
    

    def temporal_end_dict(self, query_type):

        """
        Forming the temporal end point
        :params query_type: temporal query 
        :return temporal end point: temporal endpoint consists of temporal queries
        """
        temporal_dict = {}
        
        if self.json_object[query_type]["timerel"] == "during":

            start_date_value = datetime.datetime.strptime(self.json_object[query_type]["time"], time_format)
            temporal_dict["StartDate"] = start_date_value.strftime(time_formatter)
            
            end_date_value = datetime.datetime.strptime(self.json_object[query_type]["endtime"], time_format)
            temporal_dict["EndDate"] = end_date_value.strftime(time_formatter)

            return temporal_dict


    def getData(self, end_dict):
        dictionary = {}

        try:
            url = self.url

            payload =  """<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                            <soap:Body>
                                <Get_Farmer_CropData_ByPPBNo xmlns="http://tempuri.org/">
                                <WS_UserName>{}</WS_UserName>
                                <WS_Password>{}</WS_Password>
                                <PPBNO>{}</PPBNO>
                                <StartDate>{}</StartDate>
                                <EndDate>{}</EndDate>
                                </Get_Farmer_CropData_ByPPBNo>
                            </soap:Body>
                        </soap:Envelope>""".format(self.iudx_username, self.iudx_password, end_dict["PPBNO"], end_dict["StartDate"], end_dict["EndDate"])
            headers = {
                'Content-Type': 'text/xml;charset=UTF-8'
                }

            response = requests.post(url, data=payload, headers=headers)
            status = response.status_code
            dictionary = self.fetch_response(status, response.text, dictionary)

        except requests.exceptions.HTTPError as errh:
            logging.error("An Http Error occurred: %s", errh)
            dictionary['statusCode'] = 400  # Bad Request
            dictionary['details'] = f"An Http Error occurred: {errh}"

        except requests.exceptions.ConnectionError as errc:
            logging.error("An Error Connecting to the API occurred: %s", errc)
            dictionary['statusCode'] = 503  # Service Unavailable
            dictionary['details'] = f"An Error Connecting to the API occurred: {errc}"

        except requests.exceptions.Timeout as errt:
            logging.error("A Timeout Error occurred: %s", errt)
            dictionary['statusCode'] = 504  # Gateway Timeout
            dictionary['details'] = f"A Timeout Error occurred: {errt}"

        except requests.exceptions.RequestException as err:
            logging.error("An Unknown Error occurred: %s", err)
            dictionary['statusCode'] = 500  # Internal Server Error
            dictionary['details'] = f"An Internal server Error occurred: {err}"

        except Exception as oe:
            logging.error("An Unknown Error occurred: %s", oe)
            dictionary['statusCode'] = 400  # Not Found
            dictionary['details'] = f"An unknown error occured: {oe}"

        server.publish(dictionary, self.rout_key, self.corr_id, self.method)


    def fetch_response(self, status, response, dictionary):
        
        """
        Fetches the response and status code from the API
        :param status: Status of the response
        :param response: Response from the API
        :param dictionary: Dictionary to store the response data
        :return: Updated dictionary with status and results/details
        """
        
        resp_dict = xmltodict.parse(response)

        if status == 200:
            soap = resp_dict["soap:Envelope"]["soap:Body"]
            response_json = json.loads(soap["Get_Farmer_CropData_ByPPBNoResponse"]["Get_Farmer_CropData_ByPPBNoResult"])
            success_flag = response_json["SuccessFlag"]

            if success_flag == "0":
                dictionary['statusCode'] = 204
                success_msg = response_json["SuccessMsg"]
                dictionary["details"] = success_msg
            
            else:
                dictionary['statusCode'] = status
                json_array = response_json["Data"]
                
                transformed_records = []
                for json_object in json_array:
                    
                    transformed_record ={
                        "name": json_object.get("FarmerName", None),
                        "phone": json_object.get("MobileNo", None),
                        "year ": json_object.get("FinYear", None),
                        "cropSeason": json_object.get("Season", None),
                        "districtName": json_object.get("District", None),
                        "subdistrictName": json_object.get("Mandal", None),
                        "clusterName": json_object.get("Cluster", None),
                        "villageName": json_object.get("Village", None),
                        "landIdentityInfo": {
                            "baseSurveyNumber": json_object.get("BaseSurveyNo", None),
                            "surveyNumber": json_object.get("SurveyNo", None)
                        },
                        "landExtent": json_object.get("SurveyExtent", None),
                        "irrigationSource": json_object.get("SourceofIrrigation", None),
                        "cropNameLocal": json_object.get("CropName", None),
                        "cropVarietyName": json_object.get("CropVarietyName", None),
                        "cropArea": json_object.get("CropSown_Guntas", None)
                        }
                    
                                        
                    observation_date = json_object.get("CropInfo_Dt", None)
                    
                    try:
                        transformed_record["observationDateTime"] = f"{parser.parse(observation_date).isoformat()}+05:30"
                        
                    except Exception:
                        transformed_record["observationDateTime"] = observation_date
                        
                    transformed_records.append(transformed_record)

                dictionary["results"] = transformed_records

        return dictionary
      
        
if __name__ == '__main__':

    username = config["server_setup"]["username"]
    password = config["server_setup"]["password"]
    host = config["server_setup"]["host"]
    port = config["server_setup"]["port"]
    vhost = config["server_setup"]["vhost"]
    queue = config["farmer_data_queue"]["queue"]
    url = config["get_farmer_crop_data_url"]["url"]
    iudx_username = config["iudx_credentials"]["username"]
    iudx_password = config["iudx_credentials"]["password"]
    
    fd = get_farmer_data(url, queue, iudx_username, iudx_password)
    serverconfigure = RabbitMqServerConfigure( username, password, host, port, vhost, queue)
    server = rabbitmqServer(server=serverconfigure)
    server.startserver(fd.process_request)
