from script import main


def lambda_handler(event, context):
    """
    Function for AWS Lambda microservice
    """
    fp = event.get("filepath", "./wl_posn.json")
    print("Starting handler with fp: %s", fp)
    main(fp)
