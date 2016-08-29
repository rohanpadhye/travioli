
list = null;

for (var i = 5; i >= 1; i--) {
	node = {
		data: i,
		next: list
	};
	list = node;
}

// Case 1: Not a traversal
function case1() {
	node = list;
	return node.next.next.next.data;
	// Trace: (f1, i1) (f1, i2) (f1, i3)
	// eidx1 = [(i1, 1)]       $ i1
	// eidx2 = [(i2, 1)]       $ i2
	// eidx3 = [(i3, 1)]       $ i3
}

// Case 2: Traversal
function case2() {
	node = list
	while (node.next != null) {
		node = node.next;
	}
	return node.data;
	// Trace: (f1, i1) (f1, i1) (f1, i1)
	// eidx1 = [(i1, 1)]        $ i1
	// eidx2 = [(i1, 2)]        $ i1
	// eidx3 = [(i1, 3)]        $ i1
}

function contains(node, x) {
	if (node == null) {
		return false;
	} else if (node.data == x) {
		return true;
	} else {
		return contains(node.next, x);
	}
}
// Case 3: Traversal
function case3() {
	return contains(list, 42);
	// Trace: (f2, i1) (f3, i1) (f4, i1)
		// where f2 = f1.c1, f3 = f2.c2, f4 = f3.c2
	// eidx1 = [(c1, 1), (i1, 1)]                    $ c1, i1
	// eidx2 = [(c1, 1), (c2, 1), (i1, 1)]           $ c1, c2, i1
	// eidx3 = [(c1, 1), (c2, 1), (c2, 1), (i1, 1)]  $ c1, c2, i1
}

// Case 4: Not a traversal
function case4(){
	function next(node) {
		return node.next;
	}
	return next(
		next(
			next(
				list))).data;
	// Trace: (f2, i1) (f3, i1) (f4, i1)
		// where f2 = f1.c1, f3 = f1.c2, f4 = f1.c3
	// eidx1 = [(c1, 1), (i1, 1)]  $ c1, i1
	// eidx2 = [(c2, 1), (i1, 1)]  $ c2, i1
	// eidx3 = [(c3, 1), (i1, 1)]  $ c3, i1
}

// Case 5: Traversal
function case5() {
	function next(node) {
		return node.next;
	}
	node = list
	while (node.next != null) {
		node = next(node);
	}
	// Trace: (f2, i1) (f3, i1) (f4, i1)
	   // where f2 = f1.c1, f3 = f1.c1, f4 = f1.c1
	// eidx1 = [(c1, 1) (i1, 1)]                   $ c1, i1
	// eidx2 = [(c1, 2) (i1, 1)]                   $ c1, i1
	// eidx3 = [(c1, 3) (i1, 1)]                   $ c1, i1
}


// Case 6: Traversal
function case6() {
	function next2(node) {
		return node.next;
	}

	function next(node) {
		return next2(node);
	}
	node = list
	while (node != null) {
		node = next(node);
	}
	// Trace: (f3, i1) (f5, i1) (f7, i1)
	   // where f2 = f1.c1, f3 = f2.c2, f4 = f1.c1, f5 = f4.c2, f6 = f1.c1, f7 = f6.c2
	// eidx1 = [(c1, 1), (c2, 1), (i1, 1)]        $ c1, c2, i1
	// eidx2 = [(c1, 2), (c2, 1), (i1, 1)]        $ c1, c2, i1
	// eidx3 = [(c1, 3), (c2, 1), (i1, 1)]        $ c1, c2, i1
}

// Case 7: Traversal
function case7() {
	node = list
	while (node != null) {
		node.data += 1
		node = node.next
	}
}

case1();
case2();
case3();
case4();
case5();
case6();
case7();

function repeat(f, n) {
	(function() {
		for(var i=0; i < n; i++)
			f();
	}());
}

repeat(case6, 3);
repeat(case7, 3);
repeat(case7, 3);
repeat(case7, 3);
