"""
 Copyright (c) 2016, University of California, Berkeley

 All rights reserved.

 Redistribution and use in source and binary forms, with or without
 modification, are permitted provided that the following conditions are
 met:

 1. Redistributions of source code must retain the above copyright
 notice, this list of conditions and the following disclaimer.

 2. Redistributions in binary form must reproduce the above copyright
 notice, this list of conditions and the following disclaimer in the
 documentation and/or other materials provided with the distribution.

 THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
import argparse
import collections, itertools
import csv, json
from collections import namedtuple, defaultdict
import os.path

import random
random.seed("icse2017")  # Fixed seed for reproducibility of experiments


try:
	from progressbar import ProgressBar
except ImportError:
	class ProgressBar(object):
		def __init__(self, max_value=100):
			pass
		def __enter__(self):
			return self

		def __exit__(self, exc_type, exc_value, traceback):
			pass

		def update(self, amount):
			pass

##############################
# Driver and I/O
##############################

# Global data
strings = []      # IDX -> STRING
source_map = {}   # SSID -> IID -> [LINE_START, COL_START, LINE_END, COL_END]
last_reads = {}   # MEM -> INT, map of memory location to line-number in trace where last read
line = 0          # INT
total_frames_analyzed = 0
set_funcs_analyzed = set()

# Program driver
def main() :
	global strings, source_map, line

	# Command-line arguments
	parser = argparse.ArgumentParser(description='Analyze a read-write '
    	'trace for data-structure traversals.')
	parser.add_argument('--dir', type=str, dest='dir', default='.travioli', 
        help="Working directory (default: travioli)")
	parser.add_argument('--trace_csv', type=str, dest='trace_csv', default='trace.csv', 
        help="Read-write trace file (default: trace.csv)")
	parser.add_argument('--strings_json', type=str, dest='strings_json', default='strings.json', 
        help="String pool JSON file (default: strings.json)")
	parser.add_argument('--smap_json', type=str, dest='source_map_json', default='smap.json', 
        help="Read-write trace file (default: smap.json)")
	parser.add_argument('--aec_json', type=str, dest='aec_json', default='aec.json', 
        help="AEC mappings JSON file (default: aec.json)")
	parser.add_argument('--out', type=str, dest='out', default='traversals.out', 
        help="Output file with traversal info (default: traversals.out)")
	parser.add_argument('--samples', type=int, dest='sample_size', default=10,
		help="Number of samples to randomly annotate with '*' " + \
    		"for manual evaluation (default: 10; see: paper)")


	# Parse arguments
	args = parser.parse_args()
	trace_csv_file = args.dir + '/' + args.trace_csv
	strings_json_file = args.dir + '/' + args.strings_json
	source_map_json_file = args.dir + '/' + args.source_map_json
	aec_json_file = args.dir + '/' + args.aec_json
	output_file = args.dir + '/' + args.out
	traversals_sample_size = args.sample_size
	redundant_traversals_sample_size = args.sample_size

	with open(source_map_json_file) as source_map_json:
		source_map = json.load(source_map_json)

	with open(strings_json_file) as strings_json:
		strings = json.load(strings_json)

	with open(trace_csv_file) as trace_csv:
		trace_reader = csv.reader(trace_csv)
		line = 0
		for row in trace_reader:
			line = line + 1
			read_mem = extract_read_mem(row)
			if read_mem is not None:
				last_reads[read_mem] = line
	total_lines = line

	push_sets(0, 0, 0)
	with open(trace_csv_file) as trace_csv:
		trace_reader = csv.reader(trace_csv)
		with ProgressBar(max_value=total_lines) as pb:
			line = 0
			for row in trace_reader:
				line = line + 1
				handle_row(row)
				if line % 1e3 == 0:
					pb.update(line)

	# Dump AEC table to JSON
	with open(aec_json_file, 'w') as aec_json:
		json.dump(aec_seq_tab, aec_json)


	# Dump access graphs to DOT and collect traversal infos
	traversal_infos = defaultdict(DataStructureTraversalInfo)
	for func in func_ag_map.keys():
		dot_access_graphs(func, args.dir)
		collect_traversed_data_structures(func, traversal_infos)


	# Collect totals
	set_traversed_structures = set()
	set_traversed_raecs = set()
	set_funcs_traversed = set()		
	set_redun_traversed_structures = set()
	set_redun_traversed_raecs = set()
	set_redun_funcs_traversed = set()		
	for path, ds_info in traversal_infos.iteritems():
		for raec, raec_info in ds_info.traversals.iteritems():
			func = raec_func_map[raec]
			set_traversed_structures.add(path)
			set_traversed_raecs.add(raec)
			set_funcs_traversed.add(func)
			if raec_info.redundant:
				set_redun_traversed_raecs.add(raec)
				set_redun_traversed_structures.add(path)
				set_redun_funcs_traversed.add(func)

	# Sample data-structures for reporting
	random_t_samples = set(random.sample(set_traversed_structures, 
			min(traversals_sample_size, len(set_traversed_structures))))
	random_r_samples = set(random.sample(set_redun_traversed_structures, 
			min(redundant_traversals_sample_size, len(set_redun_traversed_structures))))
		

	# Dump analysis results to output file
	with open(output_file, 'w') as out:
		#out.write("Summary for function [" + str_loc(func, full=False) + "] at " + str_loc(func, full=True) + " is:\n")
		for path, ds_info in traversal_infos.iteritems():
			out.write("+ Data structure: " + path)
			if path in random_t_samples:
				out.write(" {sampled traversal}")
			if path in random_r_samples:
				out.write(" {sampled redundancy}")
			out.write("\n")
			raec_ds_idx = 0
			for raec, raec_info in ds_info.traversals.iteritems():
				raec_ds_idx += 1
				out.write("(" + str(raec_ds_idx) + ") ")
				#if is_excluded(aec_top(raec)):
				#	out.write(" {Excluded}")
				if raec_info.redundant:
					out.write("Redundant ")
				out.write("Traversal point [" + str(raec) + "] upto " + str(raec_info.maxCount) + " times")
				out.write("\n")
				for loc in expand_aec(raec):
					out.write("    - " + str_loc(loc) + "\n")
				func = raec_func_map[raec]
				out.write("    # Analyzed Function: " + str_loc(func) + "\n")
				out.write("    # Access Graph: ag_" + str_func(func) + "\n")
				out.write("    # Reached from the following AECs: " + str_list_truncate(list(raec_read_map[raec]), 5) + "\n")
				out.write("    # Last written at the following AECs: " + str_list_truncate(list(raec_write_map[raec]), 5) + "\n")
		out.write("\n")
		out.write("Done! Analyzed " + str(total_frames_analyzed) + " activations of " + str(len(set_funcs_analyzed)) + " functions.\n")
		out.write("Traversed " + \
			str(len(set_traversed_structures)) + " data structures in " + \
		    str(len(set_funcs_traversed))  + " functions, across " + \
			str(len(set_traversed_raecs)) + " RAECs.\n")
		out.write("Redundantly traversed " + \
			str(len(set_redun_traversed_structures)) + " data structures in " + \
		    str(len(set_redun_funcs_traversed))  + " functions, across " + \
			str(len(set_redun_traversed_raecs)) + " RAECs.\n")


def str_list_truncate(seq, limit):
	if len(seq) > limit:
		seq = seq[:limit]
		seq.append("...")
	return ', '.join(map(str, seq))

# Resolves constant pool references
def string(idx):
	return str(idx) if idx >= 0 else strings[-idx-1]

# Constructor for Loc
def make_loc(sid, iid):
	return (sid, iid)

# Constructor for Val
def make_val(type, value):
	return (type, value)

# Constructor for Mem
def make_mem(ofid, offset):
	return None if ofid == 0 else (ofid, offset)

# Returns the name of the source file for an SID
str_sid_cache = {}
def str_sid(sid):
	sid = str(sid)
	if sid not in str_sid_cache:
		str_sid_cache[sid] = os.path.relpath(source_map[sid]['originalCodeFileName'])
	return str_sid_cache[sid]

# Returns string representation of a source location
# full = True returns a human-readable representation (with file-name, line/col numbers, etc)
# full = False returns simply the SID and IID 
str_loc_cache = {}
def str_loc(loc, full=True):
	(sid, iid) = loc
	sid = str(sid)
	iid = str(iid)
	if full:
		if loc not in str_loc_cache:
			str_loc_cache[loc] = str_sid(sid) + \
			  "[" + str(source_map[sid][iid][0]) + ":" + str(source_map[sid][iid][1]) + \
			  "-" + str(source_map[sid][iid][2]) + ":" + str(source_map[sid][iid][3]) + ']'
		return str_loc_cache[loc]
	else:
		return sid + ":" + iid

# Returns string representation of function
def str_func(func_loc):
	return str_loc(func_loc, full=False)

# Returns string representation of Mem
def str_mem(mem) :
	if mem == None :
		return "undefined"
	else :
		(oid, offset) = mem
		return str(oid) + "." + string(offset)

# Returns string representation of Val
def str_val(val) :
	(type, value) = val
	if type == "S" :
		return type + ":"  + string(int(value))
	else :
		return type + ":" + value

# Returns a string representation of a Call String :: [LOC]
def str_call_string(cs):
	return str(map(str_loc, cs))

# Returns if a location is within node_modules or test
def is_excluded(loc):
	src_file = str_sid(loc[0])
	return "node_modules/" in src_file or "test/" in src_file or "perf/" in src_file


##############################
# Trace Processing
##############################

# Handles one row in the trace for processing read/write sets
def handle_row(row) :
	if row[0] == "R" :
		handle_read(sid=int(row[1]), iid=int(row[2]), fid=int(row[3]), offset=int(row[4]), value=row[5], type=row[6])
	elif row[0] == "W" :
		handle_write(sid=int(row[1]), iid=int(row[2]), fid=int(row[3]), offset=int(row[4]), value=row[5], type=row[6])
	elif row[0] == "G":
		handle_getfield(sid=int(row[1]), iid=int(row[2]), rid=int(row[3]), oid=int(row[4]), offset=int(row[5]), value=row[6], type=row[7])
	elif row[0] == "P":
		handle_putfield(sid=int(row[1]), iid=int(row[2]), rid=int(row[3]), oid=int(row[4]), offset=int(row[5]), value=row[6], type=row[7])
	elif row[0] == "C":
		handle_call(sid=int(row[1]), iid=int(row[2]), func_sid=int(row[3]), func_iid=int(row[4]), func_oid=int(row[5]), fid=int(row[6]))
	elif row[0] == "E":
		handle_return(sid=int(row[1]), iid=int(row[2]), value=row[3], type=row[4])
	elif row[0] == "D":
		handle_declare(sid=int(row[1]), iid=int(row[2]), fid=int(row[3]), offset=int(row[4]), value=row[5], type=row[6])

# Extracts a memory reference from a trace log row iff it is a read or getfield
def extract_read_mem(row):
	if row[0] == "R" :
		fid=int(row[3])
		offset=int(row[4])
		return make_mem(fid, offset)
	elif row[0] == "G" :
		oid = int(row[4])
		offset = int(row[5])
		return make_mem(oid, offset)
	else :
		return None

# Processes a READ row from the trace log
def handle_read(sid, iid, fid, offset, type, value):
	global line
	loc = make_loc(sid, iid)
	mem = make_mem(fid, offset)
	val = make_val(type, value)
	read_mem(mem, loc, val)
	root_objects.add(fid)
	pass

# Processes a WRITE row from the trace log
def handle_write(sid, iid, fid, offset, type, value):
	global line
	loc = make_loc(sid, iid)
	mem = make_mem(fid, offset)
	val = make_val(type, value)
	write_mem(mem, loc, val)
	root_objects.add(fid)
	pass

# Processes a GETFIELD row from the trace log
def handle_getfield(sid, iid, rid, oid, offset, type, value):
	global line
	loc = make_loc(sid, iid)
	mem = make_mem(oid, offset)
	val = make_val(type, value)
	read_mem(mem, loc, val)
	# Hack! This is a messy way to handle reads from _proto_ objects
	# We create a fake read from base object too, so that traversal detection works out
	# This may cause some unintended bugs elsewhere
	if rid != oid:
		read_mem(make_mem(rid, offset), loc, val)
	pass

# Processes a PUTFIELD row from the trace log
def handle_putfield(sid, iid, rid, oid, offset, type, value):
	global line
	loc = make_loc(sid, iid)
	mem = make_mem(oid, offset)
	val = make_val(type, value)
	write_mem(mem, loc, val)
	# FIXME: This is a hacky way to handle writes from _proto_ objects
	# We create a fake write from base object too, so that traversal detection works out
	# This may cause some unintended bugs elsewhere
	if rid != oid:
		write_mem(make_mem(rid, offset), loc, val)
	pass

# Processes a CALL row from the trace log
def handle_call(sid, iid, func_sid, func_iid, func_oid, fid):
	global line
	loc = make_loc(sid, iid)
	push_sets(fid, loc, make_loc(func_sid, func_iid))
	pass

# Processes a RETURN row from the trace log
def handle_return(sid, iid, type, value):
	global line
	loc = make_loc(sid, iid)
	val = make_val(type, value)
	pop_sets()
	pass

# Processes a DECLARE row from the trace log
def handle_declare(sid, iid, fid, offset, type, value):
	global line
	loc = make_loc(sid, iid)
	mem = make_mem(fid, offset)
	val = make_val(type, value)
	write_mem_parent(mem, loc, val)
	pass


#################################
# Book-keeping of read/write-sets
#################################

# Global data
read_sets_stack = []    # [[FID X LOC x MEM x VAL]]  // List of reads-before-writes to a memory address, sequence per frame
write_sets_stack = []   # [{MEM}]                    // Set of memory locations written to (per frame) up to current scan
last_write_locs = {}    # MEM -> (FID x LOC)         // Map of (live) memory address to frame ID and IID of last ever write
fid_stack = []          # [INT X LOC X FUNC]    // Frame ID, last-loc-in-lower-frame (usually caller IID) and IID of callee func declaration
declarations_stack = [] # [[MEM]]               // List of "declarations" for this call stack frame
fid_stack_map = {}      # INT -> FS, where FS = [INT X LOC x FUNC]   // The entire frame stack per frame ID
fid_func_map = {}       # INT -> FUNC, where FUNC = LOC  // The IID of the syntactic function declaration/expression for this frame
aec_id_map = {}         # STR -> INT   // Maps an AEC string to an AEC identifier
aec_seq_tab = []        # INT -> [LOC] // Maps an AEC identifier to an AEC sequence
raec_cache = {}         # (FID x FID x LOC) -> AEC, where FID = INT and AEC = INT // Map of (fid_bot, fid_top, loc) to RAEC
raec_func_map = {}      # AEC -> FUNC, where AEC = INT and FUNC = LOC // Map of RAEC to function to which it is relative
raec_read_map = defaultdict(set)  # AEC -> {AEC} // Maps a relative AEC to a set of read-AECs where the reads occurred
raec_write_map = defaultdict(set) # AEC -> {AEC} // Maps a relative AEC to a set of write-AECs which supplied values that are read
root_objects = set()    # {OBJ} // Root objects (e.g. stack frames, global scope, etc)


def is_root_obj(obj):
	return obj in root_objects

def peek_read_set(depth=0) :
	return read_sets_stack[-1-depth]

def peek_write_set(depth=0):
	return write_sets_stack[-1-depth]

def peek_declarations(depth=0):
	return declarations_stack[-1-depth]

def peek_fid(depth=0):
	return fid_stack[-1-depth]

# Pushes an activation record on the call-stack
def push_sets(fid, loc, func):
	read_sets_stack.append([])
	write_sets_stack.append(set())
	fid_stack.append((fid, loc, func))
	fid_stack_map[fid] = fid_stack[:] # copy
	fid_func_map[fid] = func
	root_objects.add(fid)
	declarations_stack.append([])

# Pops an activation record from the call-stack and analyzes it (** invokes core logic **)
def pop_sets():
	(callee_fid, call_loc, func) = fid_stack.pop()
	declarations = declarations_stack.pop()
	callee_read_set = read_sets_stack.pop()
	caller_read_set = peek_read_set()
	callee_write_set = write_sets_stack.pop()
	caller_write_set = peek_write_set()

	# Warning! callee_write_set is not GC'd here, don't use it for analysis yet.

	# Collect all callee's reads into caller's reads, if not written in caller
	for read in callee_read_set:
		_, _, mem, _ = read
		if mem not in caller_write_set: 
			caller_read_set.append(read)

	# Overwrite all of callee's writes into caller's writes
	for mem in callee_write_set:
		# Bother doing this only for live memory locations, since others will be deleted from caller (below) anyway.
		if is_live(mem):
			caller_write_set.add(mem)

	# Run garbage-collection on write-set of caller
	for mem in list(caller_write_set):
		if not is_live(mem):
			caller_write_set.remove(mem)

	# Process activation
	if len(fid_stack)>=0 and not is_excluded(func):
		global total_frames_analyzed, set_funcs_analyzed
		traversed_aecs, redun_traversed_aecs = compute_traversals(callee_fid, callee_read_set)
		compute_access_graphs(func, callee_fid, callee_read_set, traversed_aecs, redun_traversed_aecs)
		total_frames_analyzed += 1
		set_funcs_analyzed.add(func)
	pass


def is_live(mem):
	return mem in last_reads and last_reads[mem] > line

def deep_kill_writes(mem):
	for i in range(len(write_sets_stack)):
		ws = write_sets_stack[i]
		ws.discard(mem)
			

# Clean up (called from GC)
def kill_writes(mem):
	ws = peek_write_set()
	ws.discard(mem)
	if mem in last_write_locs:
		pass # del last_write_locs[mem] # TODO: Figure out if this is needed

def read_mem(mem, loc, val) :
	if mem == None :
		return # Ignore reads of undefined properties
	rs = peek_read_set()
	ws = peek_write_set()
	fid, _, _ = peek_fid()
	# Mark only reads that have not been written to (in this frame) but written to at least once (globally)
	if mem not in ws and mem in last_write_locs: 
		rs.append((fid, loc, mem, val))
	# Clean up
	if not is_live(mem):
		kill_writes(mem)

def write_mem(mem, loc, val) :
	if mem == None :
		print "Write to undefined is illegal"; return; #exit()
	# Mark write to the memory location in this frame
	ws = peek_write_set()
	ws.add(mem)
	# Record global last-write to the memory location from this frame
	fid, _, _ = peek_fid()
	last_write_locs[mem] = (fid, loc)
	# Clean up
	if not is_live(mem):
		kill_writes(mem)

def write_mem_parent(mem, loc, val) :
	if mem == None :
		print "Write to undefined is illegal"; return; #exit()
	ws = peek_write_set(1)
	# Mark write to the memory location in parent frame
	ws.add(mem)
	fid, _, _ = peek_fid(1)
	# Record global last-write to the memory location from parent frame
	last_write_locs[mem] = (fid, loc)
	if not is_live(mem):
		kill_writes(mem)


#################################
# Acyclic Execution Contexts
#################################


# Computes and returns the AEC sequence for a given stack of frames
def compute_aec_seq(frame_stack):
	# At least one element needed to serve as start-node
	assert(len(frame_stack) > 0)

	# Store edges in reverse, from a func to its predecessor
	# with the call-site on the edge label and remember the path
	# length from the root.
	redges = {} # FUNC -> FUNC X LOC X INT

	# Start node is the first function in the stack
	(first_fid, caller_site, first_func) = frame_stack[0]

	# Initialize cost of first_func to 0 with no back-edge
	redges[first_func] = (None, None, 0)

	# Process remaining stack and add back-edges with shortest-path
	last_func = None
	for (fid, call_site, func) in frame_stack:
		if func not in redges:
			cost = redges[last_func][2]+1
			redges[func] = (last_func, call_site, cost)
		last_func = func

	# Either first_func is global scope which cannot be called,
	# or first_func is a base function and last_func is a dummy end-node
	assert(last_func != first_func)

	# Now find the path in reverse order from last_func to first_func
	total_cost = redges[last_func][2]
	aec_seq = []
	while last_func != first_func:
		(last_func, call_site, cost) = redges[last_func]
		aec_seq.append(call_site)

	# Reverse the call-chain to get the correct value
	aec_seq.reverse()

	# Validate and return the ACC
	assert(len(aec_seq) == total_cost)
	return aec_seq

# Return an AEC identifier for given AEC sequence
def get_aec_id(aec_seq) : # FIXME: Map keys are string representations of 
	global aec_id_map
	aec_str = '+'.join(map(str, aec_seq))
	if aec_str not in aec_id_map:
		aec_id_map[aec_str] = len(aec_seq_tab)
		aec_seq_tab.append(aec_seq)
	return aec_id_map[aec_str]


# Return an AEC sequence to an AEC identifier
def expand_aec(aec):
	return reversed(aec_seq_tab[aec])

# Return the traversal-point for an AEC
def aec_top(aec):
	return aec_seq_tab[aec][-1]


# Compute the relative AEC from a base frame, a stack top and current location
def get_raec(fid_bot, fid_top, loc):
	# Check cache first
	key = (fid_bot, fid_top, loc)
	if key in raec_cache:
		return raec_cache[key]
	else:
		# Get relevant portion of frame stack
		bot_idx = -1
		stack = fid_stack_map[fid_top]
		for i, (fid, call_site, func) in enumerate(stack):
			if fid == fid_bot:
				bot_idx = i
				break
		assert(bot_idx >= 0)
		# Construct the relative execution context (REC)
		rec_seq = stack[bot_idx:]
		rec_seq.append((None, loc, "__dummy_end_node__"))
		# Reduce to the relative acyclic execution context (RAEC)
		raec_seq = compute_aec_seq(rec_seq)
		assert(raec_seq[-1] == loc)
		# Get unique AEC identifier for this AEC sequence
		raec_id = get_aec_id(raec_seq)
		raec_cache[key] = raec_id
		raec_func_map[raec_id] = fid_func_map[fid_bot]
		return raec_id


#################################
# Detecting Traversals
#################################



# An edge in the traversals computation has an Object ID as the source (may be Frame ID),
# an Object ID as the destination (or a dummy value if the read value was a primitive),
# and a 3-part label, consisting of:
#  (i)   the field (offset) being read
#  (ii)  the Acyclic Execution Context (AEC) identifier
#  (iii) the actual value being read - this has some redundancy if the value read was an Object type,
#          since the edge target has the same object ID as in the value label.
Edge = namedtuple('Edge', ['srcObj', 'field', 'aec', 'val', 'dstObj'])

# Compute traversals for the given activation record fid_bot and the computed read-trace
def compute_traversals(fid_bot, read_set) :
	heap_edges = []                      # [EDGE]
	heap_aec_map = {}                    # AEC -> [EDGE]
	ancestors = {}                       # OBJ -> [OBJ]
	traversed_aecs = set()               # {AEC}
	multi_traversed_aecs = set()         # {AEC}

	# Returns whether an edge has a Frame ID as its source
	def is_root(edge):
		return is_root_obj(edge.srcObj)

	# Convert each read in the read set to an edge in the read graph
	for (fid_top, loc, mem, val) in read_set:
		# The source node is the object being read, and the field is part of the label
		src, fld = mem
		# The destination is the object ID if the value is an object, or a default value otherwise
		typ, value = val
		dst = int(value) if typ == 'O' else 0
		# The Acyclic Execution Context (AEC) is the Acyclic Calling Context + Source Location of read
		aec = get_raec(fid_bot, fid_top, loc)

		# Create an edge for traversal detection
		edge = Edge(src, fld, aec, val, dst) 

		# Populate ancestors of dst if dst is an object
		# Note: This won't be accurate for cyclic graphs but should work for our purposes
		if dst > 0:	
			# Make sure there is an ancestor set for dst
			if dst not in ancestors:
				ancestors[dst] = set()
			# Make sure that the src (and all its ancestors) are also ancestors of dst
			if src in ancestors:
				ancestors[dst].update(ancestors[src])
			else:
				ancestors[dst].add(src)
			# Finally, every node is an ancestor of itself
			ancestors[dst].add(dst)

		# Optimization: Maintain only heap edges since stack edges cannot be traversed
		if is_root(edge) :
			# fid = src, var = fld
			pass # ??
		else :
			heap_edges.append(edge)
			if aec not in heap_aec_map:
				heap_aec_map[aec] = []
			heap_aec_map[aec].append(edge)

		# Map to read-AEC and last-write-AEC
		read_aec = get_raec(0, fid_top, loc)
		raec_read_map[aec].add(read_aec)
		last_write_fid, last_write_loc = last_write_locs[mem]
		last_write_aec = get_raec(0, last_write_fid, last_write_loc)
		raec_write_map[aec].add(last_write_aec)


	# Returns true if o1 is an ancestor of o2 or vice versa
	def path_exists(o1, o2):
		return (o2 in ancestors and o1 in ancestors[o2]) or \
			   (o1 in ancestors and o2 in ancestors[o1])


	def is_traversal_by_ancestry(edges):
		if len(edges) <= 1:
			return False
		mems = set()
		for e in edges:
			mems.add((e.srcObj, e.field))
		if len(mems) <= 1:
			return False
		common_ancestors = set(ancestors.keys())
		for e in edges:
			obj = e.srcObj
			if obj not in ancestors:
				return False
			common_ancestors &= ancestors[obj]
			if len(common_ancestors) == 0:
				return False
		else:
			return True

	def is_traversal_by_connectivity(edges):		
		for i in range(len(edges)):
			if i > 100:  # FIXME! Bail-out early if it seems like traversal is unlikely
				return False 
			e1 = edges[i]
			for j in range(i):
				e2 = edges[j]
				if (e1.srcObj != e2.srcObj or e1.field != e2.field) and path_exists(e1.srcObj, e2.srcObj):
					return True
		else:
			return False


	# Look for traversals in each AEC and collect candidate roots
	for aec, edges in heap_aec_map.iteritems():
		# Early stop for obvious non-traversals
		if len(edges) == 1:
			continue


		if not is_traversal_by_connectivity(edges):
			continue


		# Mark AEC as traversed
		traversed_aecs.add(aec)

		# Now, try to determine if the traversal was redundant by looking at the sequence
		# of memory locations de-referenced (and if this sequence repeats)
		first_mem = (edges[0].srcObj, edges[0].field)
		mem_sequences = []
		fields_differ = False
		for e in edges:
			mem = (e.srcObj, e.field)
			fields_differ |= (e.field != first_mem[1])
			if mem == first_mem:
				mem_sequences.append([])
			mem_sequences[-1].append(mem)


		# Sort sequences by length in descending order
		mem_sequences = sorted(mem_sequences, key=len, reverse=True)
		# Early cut-off if too few sequences
		min_sequences = 2 if fields_differ else 3
		min_non_trivial_sequences = 1 if fields_differ else 2
		assert(min_sequences > min_non_trivial_sequences)
		if len(mem_sequences) < min_sequences:
			continue
		for k in range(min_non_trivial_sequences):
			if len(mem_sequences[k]) < 2:
				break
		else:
			assert(len(mem_sequences[0]) > 1) # this is ensured because a traversal has at least two distinct mems
			# If each sequence is a prefix of the first sequence, then we 
			# have a repetition. Try to contradict this.
			s1 = mem_sequences[0]
			for k in range(1, len(mem_sequences)):
				s2 = mem_sequences[k]
				if not is_prefix(s2, s1):
					break
			else:
				# If no break then all sequences are prefixes of the longest
				# sequence, and hence this is a multi-traversal
				multi_traversed_aecs.add(aec)
				#print [str_mem((e.srcObj, e.field)) for e in edges]
				#print "Redundant traversal at AEC " + str(aec) + " in clumps: " + ','.join(map(str, map(len, mem_sequences)))
		

	return traversed_aecs, multi_traversed_aecs 



# A function to determine if seq1 is a prefix of seq2
def is_prefix(seq1, seq2):
	if len(seq1) > len(seq2):
		return False
	for i in range(len(seq1)):
		if not seq1[i] == seq2[i]:
			return False
	else:
		return True

#################################
# Access Graphs
#################################

# Global data
func_ag_map = {} # FUNC -> AG // A map of functions to their access graphs

# Helper function for quoting strings 
# (assuming they don't contain quotes themselves; 
#	no escaping performed)
def quote(string):
	return '"' + string + '"'

# Get or create an access graph for a function
def get_access_graph(func):
	global func_ag_map
	if func in func_ag_map:
		ag = func_ag_map[func]
	else:
		nodes = {}    # (AEC|FunctionLoc|$) -> Node
		roots = []    # [Node]
		ag = (nodes, roots)
		func_ag_map[func] = ag
	return ag

class AccessGraphNode(object):
	__slots__ = ['idx', 'name', 'label', 'maxCount', 'edgeTo', 'marked']
	def __init__(self, idx, name, label):
		self.idx = idx
		self.name = name
		self.label = label
		self.edgeTo = dict() # DST_NODE x LABEL
		self.marked = False
		self.maxCount = 0

	def addEdge(self, dst_idx, label):
		# If there is an edge to same dest with different label, merge them
		if dst_idx in self.edgeTo and self.edgeTo[dst_idx] != label:
			self.edgeTo[dst_idx] = '(*)'
		else:
			self.edgeTo[dst_idx] = label

	def iterEdges(self):
		return self.edgeTo.iteritems()

	def __enter__(self):
		self.marked = True
		return self

	def __exit__(self, exc_type, exc_value, traceback):
		self.marked = False

	def updateMaxCount(self, count):
		if count > self.maxCount:
			self.maxCount = count


class AccessGraphRootNode(AccessGraphNode):
	__slots__ = ['pathPrefix']
	def __init__(self, idx, name, label):
		AccessGraphNode.__init__(self, idx, name, label)
		self.pathPrefix = None

class AccessGraphFuncNode(AccessGraphRootNode):
	def __init__(self, func):
		idx = func
		label = str_func(func)
		name = quote(label)
		AccessGraphRootNode.__init__(self, idx, name, label)

class AccessGraphVarNode(AccessGraphNode):
	# var : FUNC x FIELD
	def __init__(self, var):
		func = var[0]
		fld = var[1]
		idx = var
		label = string(fld) + '@' + str_func(func)
		name = quote(label)
		AccessGraphNode.__init__(self, idx, name, label)

class AccessGraphAecNode(AccessGraphNode):
	__slots__ = ['aec', 'traversed', 'redundant']
	def __init__(self, aec):
		AccessGraphNode.__init__(self, aec, str(aec), str(aec))
		self.aec = aec
		self.marked = False
		self.traversed = False
		self.redundant = False

# Construct and/or merge-into access graphs for an activation
def compute_access_graphs(func, fid_bot, read_set, traversed_aecs, redun_traversed_aecs):
	# Get the access graph for this function or create one
	nodes, roots = get_access_graph(func)

	# Root idx/name referring to global vars
	root_idx = 'global' 

	# This map is used to track what AEC an object was last read at, which is usually a 
	# good estimate for the referrer
	last_seen = {}  # OBJ -> AEC

	# Counter for aec nodes seen in this activation
	aec_counts = defaultdict(int)

	# Helper function to create or retrieve an AEC node
	def get_aec_node(aec):
		# If no node exists for this AEC, create one
		if aec not in nodes:
			node = AccessGraphAecNode(aec)
			nodes[aec] = node
		else:
			node = nodes[aec]
		aec_counts[aec] += 1
		node.traversed = node.traversed or aec in traversed_aecs
		node.redundant = node.redundant or aec in redun_traversed_aecs
		return node

	# Helper function to create or retrieve a function node
	def get_func_node(func):
		# If no node exists for this func, create one
		if func not in nodes:
			node = AccessGraphFuncNode(func)
			node.pathPrefix = '('+str_loc(func,full=True)+')'
			nodes[func] = node
			roots.append(node)  
		else:
			node = nodes[func]
		return node

	# Helper function to create or retrieve root node
	def get_root_node():
		if root_idx not in nodes:
			root_node = AccessGraphRootNode(root_idx, root_idx, root_idx)
			root_node.pathPrefix = '<global>'
			nodes[root_idx] = root_node
			roots.append(root_node) 
		return nodes[root_idx] 


	# Helper function to create or retrieve a var node
	# Here, var is a pair of (func, fld) or (root_idx, fld)
	def get_var_node(var):
		# If no node exists for this var, create one
		if var not in nodes:
			node = AccessGraphVarNode(var)
			nodes[var] = node
		else:
			node = nodes[var]
		return node

	# Process read-events sequentially
	for (fid_top, loc, mem, val) in read_set:
		# Extract the object being read and the field being de-referenced
		obj, fld = mem
		# Extract the value being read
		typ, value = val
		if typ == 'O':
			res = int(value)
		else:
			res = None

		# The Acyclic Execution Context (AEC) is the Acyclic Calling Context + Source Location of read
		aec = get_raec(fid_bot, fid_top, loc)
		# Add an edge from AEC where obj was last-seen or else root to this AEC
		label = string(fld)
		if obj in last_seen:
			last_seen_idx = last_seen[obj]
			src_idx = last_seen_idx
			src_node = nodes[last_seen_idx]
			dst_idx = aec
			dst_node = get_aec_node(aec)
		elif is_root_obj(obj):
			# Try to find func for the source (else probably a global)
			if obj in fid_func_map:
				func = fid_func_map[obj]
				src_idx = func
				src_node = get_func_node(func)
				var = (func, fld)
				dst_idx = var
				dst_node = get_var_node(var)
			else:
				src_idx = root_idx
				src_node = get_root_node()
				var = ((0,0), fld)
				dst_idx = var
				dst_node = get_var_node(var)
		else:
			continue

		# Map the result to be last seen at the destination node of the edge
		# Note: This is done late so that if there is a trivial cycle (OBJ.FLD == OBJ)
		# then last_seen accessed above should first handle the read and then the write
		# should update the last_seen
		if res is not None:
			last_seen[res] = dst_idx


		# Create edge from source to destination
		src_node.addEdge(dst_idx, label)

	# Update AEC max-counts
	for aec in aec_counts.iterkeys():
		nodes[aec].updateMaxCount(aec_counts[aec])


# Dump access graph for a function to a DOT file
def dot_access_graphs(func, parent_dir):
	# Get access graph for this function
	nodes, roots = get_access_graph(func)

	# Dump access graphs to dot files
	dot_file_name = parent_dir + '/ag_' + str_loc(func, full=False) + '.dot'
	with open(dot_file_name, 'w') as dot_file:
		dot_file.write('digraph access_graph {\n')
		dot_file.write('rankdir="LR"\n')
		dot_file.write('node [style="filled"]\n')
		# Print graph nodes in GraphViz format
		for key, node in nodes.items():
			if isinstance(node, AccessGraphAecNode) and node.redundant:
				fillcolor = 'black'
				fontcolor = 'white'
			elif isinstance(node, AccessGraphAecNode) and node.traversed:
				fillcolor = 'grey'
				fontcolor = 'black'
			else:
				fillcolor = 'white'
				fontcolor = 'black'
			node_name = node.name
			node_label = node.label
			dot_file.write(node_name + ' [fillcolor="' + fillcolor + '", fontcolor="' + fontcolor + '", label = "' + node_label + '"]\n')

			# Print graph edges in GraphViz format
			for dst_idx, edge_label in node.iterEdges():
				src_node = node
				dst_node = nodes[dst_idx]
				src_name = src_node.name
				dst_name = dst_node.name
				dot_file.write(src_name + ' -> ' + dst_name + ' [label = "' + edge_label + '"]\n')
		dot_file.write('}\n')


# Traverse access graphs for a function from the root node(s) to 
# determine the root access paths and collect traversal infos
def collect_traversed_data_structures(func, traversal_infos):
	# Get access graph for this function
	nodes, roots = get_access_graph(func)

	def collect_traversed_aecs(aec_node, traversal_info):
		# Don't process the same node more than once
		if not aec_node.marked:
			with aec_node:
				# Collect traversal info regarding AEC
				if aec_node.traversed:
					traversal_info.addAecNode(aec_node)
				for dst_idx, label in aec_node.iterEdges():
					dst_node = nodes[dst_idx]
					collect_traversed_aecs(dst_node, traversal_info)

	def process_traversed_paths(node, path):
		# Prevent cycles
		if not node.marked:
			with node:
				# Process all out-going edges
				for dst_idx, label in node.iterEdges():
					dst_node = nodes[dst_idx]
					# If child-edge is a traversal, collect info for this access path and don't recurse further
					if isinstance(dst_node, AccessGraphAecNode) and dst_node.traversed:
						path_str = '.'.join(path)
						info = traversal_infos[path_str]
						info.addFunc(func)
						collect_traversed_aecs(dst_node, info)
					else:
						# Otherwise recursive into destination node with new access path
						process_traversed_paths(dst_node, path + [label])


	# Process and print info
	for root_node in roots:
		process_traversed_paths(root_node, [root_node.pathPrefix])


# Information about a data-structure being traversed
class DataStructureTraversalInfo(object):
	__slots__ = ["funcs", "traversals"]
	def __init__(self):
		self.funcs = set()
		self.traversals = defaultdict(AecTraversalInfo)

	def addAecNode(self, aec_node):
		aec = aec_node.aec
		aec_info = self.traversals[aec]
		aec_info.redundant |= aec_node.redundant
		aec_info.maxCount = max(aec_info.maxCount, aec_node.maxCount)

	def addFunc(self, func):
		self.funcs.add(func)


# Information about an AEC being traversed
class AecTraversalInfo(object):
	__slots__ = ["redundant", "maxCount"]
	def __init__(self):
		self.redundant = False
		self.maxCount = 1



# Run the program driver
if __name__ == "__main__":
	main()
