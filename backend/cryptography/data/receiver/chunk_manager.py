import os
import json
from datetime import datetime
from multiprocessing import Pool
import threading
from queue import Queue
from math import ceil
from utils.logging import LogType, log

def collect_chunks(chunk_logfile_path, general_logfile_path, chunk_data, chunk_output_dir, chunk_num):
    try:
        os.makedirs(chunk_output_dir, exist_ok=True)
        chunk_name = f"chunk_{chunk_num}"
        chunk_path = os.path.join(chunk_output_dir, f"{chunk_name}.pchunk")
        with open(chunk_path, 'wb') as f:
            f.write(chunk_data)
        #log for saved chunk
        log(f"Chunk {chunk_name} saved at {chunk_path}", log_type=LogType.INFO, status="Success", general_logfile_path=general_logfile_path)
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
                    log("Invalid JSON in chunk log file, starting over.", log_type=LogType.ERROR, status="Failure", general_logfile_path=general_logfile_path)
                    pass
        if 'chunk_output_dir' not in existing_data:
            existing_data['chunk_output_dir'] = chunk_output_dir
        existing_data.update(new_entry)
        with open(chunk_logfile_path, 'w') as f:
            json.dump(existing_data, f, indent=2)
        #log for updated chunk log file
        log(f"Chunk log file updated at {chunk_logfile_path}", log_type=LogType.INFO, status="Success", general_logfile_path=general_logfile_path)
    except Exception as e:
        #log for error in collect_chunks
        log(f"Error collecting chunk {chunk_name}: {e}", log_type=LogType.ERROR, status="Failure", general_logfile_path=general_logfile_path)
        raise

def collect_chunks_wrapper(args):
    collect_chunks(*args)

def collect_chunks_parallel(chunk_list, chunk_logfile_path, general_logfile_path, chunk_output_dir):
    log("Parallel chunk collection initiated", LogType.INFO, "Started", general_logfile_path)

    tasks = []
    for chunk_data, chunk_num in chunk_list:
        tasks.append((chunk_logfile_path, general_logfile_path, chunk_data, chunk_output_dir, chunk_num))

    with Pool(processes=4) as pool:
        pool.map(collect_chunks_wrapper, tasks)

    log("Parallel chunk collection completed", LogType.INFO, "Success", general_logfile_path)

def read_chunk_batch(batch_nums, output_dir, chunk_size, queue):
    for num in batch_nums:
        chunk_path = os.path.join(output_dir, f"chunk_{num}.pchunk")
        if os.path.exists(chunk_path):
            with open(chunk_path, 'rb') as f:
                data = f.read()
            os.remove(chunk_path)
            offset = (num - 1) * chunk_size
            queue.put((offset, data))

def join_chunks(chunk_output_dir, chunk_logfile_path,general_logfile_path, chunk_size=8192, batch_size=100):
    try:
        with open(chunk_logfile_path, 'r') as log_file:
            try:
                chunk_info = json.load(log_file)
            except json.JSONDecodeError as e:
                log(f"Invalid JSON in chunk log file: {e}", log_type=LogType.ERROR, status="Failure", general_logfile_path=general_logfile_path)
                raise
        
        output_dir = chunk_info.get("chunk_output_dir")
        final_file_path = os.path.join(chunk_output_dir, 'final_file.zstd')
        chunk_nums = []
        num = 1
        while os.path.exists(os.path.join(output_dir, f"chunk_{num}.pchunk")):
            chunk_nums.append(num)
            num += 1

        queue = Queue()
        threads = []

        for i in range(0, len(chunk_nums), batch_size):
            batch = chunk_nums[i:i + batch_size]
            t = threading.Thread(target=read_chunk_batch, args=(batch, output_dir, chunk_size, queue))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        with open(final_file_path, 'wb') as final_file:
            data_list = []
            while not queue.empty():
                data_list.append(queue.get())
            for offset, data in sorted(data_list):  # Sort to maintain order
                final_file.seek(offset)
                final_file.write(data)
            # for chunk_name, info in chunks:
            #     chunk_path = info.get('path')
            #     if not chunk_path or not os.path.exists(chunk_path):
            #         #log for missing chunk
            #         log(f"Chunk file {chunk_path} not found for chunk {chunk_name}", log_type=LogType.ERROR, status="Failure", general_logfile_path=general_logfile_path)
            #         continue
            #     with open(chunk_path, 'rb') as chunk_file:
            #         final_file.write(chunk_file.read())
            #     os.remove(chunk_path)
            #     #log for successfully added chunk
            #     log(f"Chunk {chunk_name} added to final file {final_file_path}", log_type=LogType.INFO, status="Success", general_logfile_path=general_logfile_path)

        log(f"All chunks successfully joined into {final_file_path}", log_type=LogType.INFO, status="Success", general_logfile_path=general_logfile_path)
        return final_file_path

    except Exception as e:
        log(f"Error joining chunks: {e}", log_type=LogType.ERROR, status="Failure", general_logfile_path=general_logfile_path)
        raise
