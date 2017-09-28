
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
}

// Case 2: Traversal
function case2() {
	node = list
	while (node.next != null) {
		node = node.next;
	}
	return node.data;
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
}

// Case 4: Not a traversal
function case4(){
	function next(node) {
		return node.next;
	}
	return next(next(next(list))).data;
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

// Some redundant traversals
repeat(case6, 3);
repeat(case7, 3);
repeat(case7, 3);
repeat(case7, 3);
