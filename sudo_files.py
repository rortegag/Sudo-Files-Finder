import os
import concurrent.futures
from tqdm import tqdm

def find_files_with_sudo(directory):
    files_with_sudo = []
    subdirectories = []

    try:
        for entry in os.scandir(directory):
            if entry.is_file(follow_symlinks=False) and "sudo" in entry.name:
                files_with_sudo.append(entry.path)
            elif entry.is_dir(follow_symlinks=False):
                subdirectories.append(entry.path)
    except PermissionError:
        pass  # Ignorar los directorios a los que no se tiene acceso
    except OSError as e:
        if e.errno != 40:  # No es el error de demasiados niveles de enlaces simbólicos
            raise

    return files_with_sudo, subdirectories

def find_files_with_sudo_parallel(start_dir):
    files_with_sudo = []
    directories = [start_dir]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        with tqdm(total=1, unit="dir") as pbar:
            while directories:
                future_to_directory = {executor.submit(find_files_with_sudo, dir): dir for dir in directories}
                directories = []

                for future in concurrent.futures.as_completed(future_to_directory):
                    dir = future_to_directory[future]
                    try:
                        result_files, result_dirs = future.result()
                        files_with_sudo.extend(result_files)
                        directories.extend(result_dirs)
                        pbar.update(len(result_dirs))
                        pbar.total += len(result_dirs) - 1
                    except Exception as exc:
                        print(f"Error scanning {dir}: {exc}")

    return files_with_sudo

def separate_files_by_owner(files):
    root_owned_files = []
    non_root_owned_files = []

    for file in files:
        try:
            stat_info = os.stat(file)
            if stat_info.st_uid == 0:
                root_owned_files.append(file)
            else:
                non_root_owned_files.append(file)
        except FileNotFoundError:
            pass  # Ignorar archivos que no se encuentran (podrían haber sido eliminados durante el escaneo)
        except PermissionError:
            pass  # Ignorar archivos a los que no se tiene acceso

    return root_owned_files, non_root_owned_files

if __name__ == "__main__":
    start_dir = "/"
    all_files = find_files_with_sudo_parallel(start_dir)
    root_files, non_root_files = separate_files_by_owner(all_files)

    print("Files owned by root:")
    for file in root_files:
        print(file)

    print("\nFiles not owned by root:")
    for file in non_root_files:
        print(file)
