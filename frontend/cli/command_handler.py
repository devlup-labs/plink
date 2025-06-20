from argument_parser import get_parser

def arguments_dictionary():
    parser = get_parser()
    args = parser.parse_args()
    
    args_dictionary = {
        'method': args.method,
        'port': args.port,
        'encryption': args.encryption,
        'chunk_size': args.chunk_size,
        'compress': args.compress,
        'password': args.password,
        'resume': args.resume,
        'verify': args.verify,
        'output_directory': args.output_directory,
        'auto_accept': args.auto_accept,
        'max_size': args.max_size
    }

    return args_dictionary