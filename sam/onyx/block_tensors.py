def get_position(crd_arr, crd):
    res = next(i for i, val in enumerate(crd_arr)
                                  if val >= crd)
    return res
    
# Write file with block sizes
def write_glb_triple(b, c, d, tensor_name, pack=True):
    pass

# Write file with block sizes
def write_glb_double(b, c, tensor_name, pack=True):
    pass

def pack_single(b, glb_size, memtile_size):
    # TODO: not implemented
    return b
    
def process_glb_vecscalarmul(b, name, out_file, out_name, 
                             glb_size=131072, memtile_size=1024, memtile_crd_space=True, pack=True)
    b_new = block_vvecscalarmul(b, name, glb_size, memtile_size, memtile_crd_space)
    if pack:
        b_new = pack_single(b_new, glb_size, memtile_size)
    write_glb_single(b_new, out_file, out_name)
    
# Write file with block sizes
def write_glb_single(b, out_file, out_name):
    b_shape = b["shape"]
    b_segi = b["tensor_b_mode_0_seg"]
    b_crdi = b["tensor_b_mode_0_crd"]
    
    
    output_lines = []
    
    # TODO: may need to fix this later
    assert len(b_segi) < memtile_size
    output_lines.append(len(b_segi))
    output_lines.append(b_segi)
    
    for i in range(len(b_segi)-1):
        start_pos = b_segi[i]
        stop_pos = b_segi[i+1]
        fiber_size =  stop_pos - start_pos
        output_lines.append(fiber_size)
        for i in range(start_pos, stop_pos):
            output_lines.append(b_crdi[i])
        output_lines.append

    out_path = f"{out_dir}/{out_name}"
    with open(out_path, "w+") as curr_file:
        curr_file.writelines(output_lines)

    
    
# Sizes are in elements. Each element is 2B
def block_vecscalarmul(b, tensor_name, glb_size=131072, memtile_size=1024, memtile_crd_space=True):
    print("Blocking vec scalar mul for", tensor_name + "...")
    
    b_shape = b["shape"]
    b_segi = b["tensor_b_mode_0_seg"]
    b_crdi = b["tensor_b_mode_0_crd"]
    print(b_segi)
    
    b_segi_new = []
    
    # Block to fit into GLB
    assert b_segi[-1] < glb_size # Ignore for now
    
    
    # If a fiber is too big, block that fiber into coordinates of 1024...
    
    # Loop through all of the fibers
    for i in range(len(b_segi)-1):
        start_pos = b_segi[i]
        stop_pos = b_segi[i+1]
        last_fiber = stop_pos >= len(b_crdi)
        fiber_size =  stop_pos - start_pos
        
        # If fiber is too large
        if fiber_size > memtile_size:
            if last_fiber:
                fiber = b_crdi[start_pos:]
            else:
                fiber = b_crdi[start_pos: stop_pos]
            
            if memtile_crd_space:
                b_segi_new.append(start_pos)
                print(fiber[0], fiber[-1])
                print(fiber)
                for crd in range(0, fiber[-1], memtile_size):
                    pos = start_pos + get_position(fiber, crd)
                    b_segi_new.append(pos)
            else:
                raise NotImplemented
        else: 
            b_segi_new.append(stop_pos)
            
    b_segi_new.append(b_segi[i+1])
    print(b_segi_new)
    b_new = b.copy()
    b_new["tensor_b_mode_0_seg"] = b_segi_new
    return b_new 
    
def get_fiber_sizes(b):
    result = []
    b_shape = b["shape"]
    b_segi = b["tensor_b_mode_0_seg"]
    b_crdi = b["tensor_b_mode_0_crd"]
    
    # Loop through all of the fibers
    for i in range(len(b_segi)-1):
        start_pos = b_segi[i]
        stop_pos = b_segi[i+1]
        last_fiber = stop_pos >= len(b_crdi)
        fiber_size =  stop_pos - start_pos
        result.append(fiber_size)
    return result
