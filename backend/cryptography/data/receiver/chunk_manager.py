import os
import json
from datetime import datetime
from logging import Logtype, log


def collect_chunks(chunk_logfile_path, general_logfile_path, chunk_data, chunk_output_dir, chunk_name):
    try:
        os.makedirs(chunk_output_dir, exist_ok=True)
        chunk_path = os.path.join(chunk_output_dir, f"{chunk_name}.pchunk")

        with open(chunk_path, 'wb') as f:
            f.write(chunk_data)
        #log for saved chunk
        log(f"Chunk {chunk_name} saved at {chunk_path}", log_type=Logtype.INFO, status="Success", general_logfile_path)
        new_entry = {
            chunk_name: {
                "path": chunk_path,
                "creation_time": datetime.now().isoformat()
            }
        }

        existing_data = {}
        if os.path.exists(chunk_logfile_path):
            with open(chunk_logfile_path, 'r') as f:
                try:
                    existing_data = json.load(f)
                except json.JSONDecodeError:
                    #log for invalid JSON and starting over
                    log(f"Invalid JSON in chunk log file, starting over.", log_type=Logtype.ERROR, status="Failure", general_logfile_path)
                    pass

        existing_data.update(new_entry)
        with open(chunk_logfile_path, 'w') as f:
            json.dump(existing_data, f, indent=2)
        #log for updated chunk log file
        log(f"Chunk log file updated at {chunk_logfile_path}", log_type=Logtype.INFO, status="Success", general_logfile_path)
    except Exception as e:
        #log for error in collect_chunks
        log(f"Error collecting chunk {chunk_name}: {e}", log_type=Logtype.ERROR, status="Failure", general_logfile_path)
        raise

def join_chunks(chunk_output_dir, chunk_logfile_path,general_logfile_path):
    try:
        if not os.path.exists(chunk_logfile_path):
            raise FileNotFoundError(f"Log file not found: {chunk_logfile_path}")

        with open(chunk_logfile_path, 'r') as log_file:
            try:
                chunk_info = json.load(log_file)
            except json.JSONDecodeError as e:
                #log(LogType.ERROR, f"Invalid JSON in chunk log file: {e}", None)
                log(f"Invalid JSON in chunk log file: {e}", log_type=Logtype.ERROR, status="Failure", general_logfile_path)
                raise

        if not isinstance(chunk_info, dict):
            raise ValueError("Chunk log file does not contain a valid dictionary.")

        chunks = sorted(chunk_info.items(), key=lambda x: x[0])
        final_file_path = os.path.join(chunk_output_dir, 'final_file.zstd')

        with open(final_file_path, 'wb') as final_file:
            for chunk_name, info in chunks:
                chunk_path = info.get('path')
                if not chunk_path or not os.path.exists(chunk_path):
                    #log for missing chunk
                    log(f"Chunk file {chunk_path} not found for chunk {chunk_name}", log_type=Logtype.ERROR, status="Failure", general_logfile_path)
                    continue
                with open(chunk_path, 'rb') as chunk_file:
                    final_file.write(chunk_file.read())
                os.remove(chunk_path)
                #log for successfully added chunk
                log(f"Chunk {chunk_name} added to final file {final_file_path}", log_type=Logtype.INFO, status="Success", general_logfile_path)


        #log for successfully joined chunks
        log(f"All chunks successfully joined into {final_file_path}", log_type=Logtype.INFO, status="Success", general_logfile_path)


        #log for successfully joined chunks
        return final_file_path

    except Exception as e:
        #log for error in join_chunks
        log(f"Error joining chunks: {e}", log_type=Logtype.ERROR, status="Failure", general_logfile_path)
        raise
