import os
from installed_clients.DataFileUtilClient import DataFileUtil

def unwrap_assemblies(dfu: DataFileUtil, refs, scratch):
    """Accepts Assembly or AssemblySet refs; returns (paths, labels)."""
    paths, labels = [], []
    for ref in refs:
        obj = dfu.get_objects({'object_refs':[ref]})['data'][0]
        otype = obj['info'][2]
        if otype.startswith('KBaseSets.AssemblySet'):
            for el in obj['data']['elements']:
                p2, l2 = unwrap_assemblies(dfu, [el['ref']], scratch)
                paths += p2; labels += l2
        else:
            name = obj['info'][1].split('-')[0]
            handle = obj['data']['fasta_handle_ref']
            path = dfu.shock_to_file({'handle_id': handle,
                                      'file_path': os.path.join(scratch, f'{name}.fa')})['file_path']
            paths.append(path); labels.append(name)
    return paths, labels
