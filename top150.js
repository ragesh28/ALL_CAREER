const top150Data = [
    // --- ARRAYS & HASHING ---
    { "id": 1, "title": "Two Sum", "difficulty": "Easy", "topic": "Arrays & Hashing", "url": "https://leetcode.com/problems/two-sum/" },
    { "id": 217, "title": "Contains Duplicate", "difficulty": "Easy", "topic": "Arrays & Hashing", "url": "https://leetcode.com/problems/contains-duplicate/" },
    { "id": 242, "title": "Valid Anagram", "difficulty": "Easy", "topic": "Arrays & Hashing", "url": "https://leetcode.com/problems/valid-anagram/" },
    { "id": 1929, "title": "Concatenation of Array", "difficulty": "Easy", "topic": "Arrays & Hashing", "url": "https://leetcode.com/problems/concatenation-of-array/" },
    { "id": 49, "title": "Group Anagrams", "difficulty": "Medium", "topic": "Arrays & Hashing", "url": "https://leetcode.com/problems/group-anagrams/" },
    { "id": 347, "title": "Top K Frequent Elements", "difficulty": "Medium", "topic": "Arrays & Hashing", "url": "https://leetcode.com/problems/top-k-frequent-elements/" },
    { "id": 238, "title": "Product of Array Except Self", "difficulty": "Medium", "topic": "Arrays & Hashing", "url": "https://leetcode.com/problems/product-of-array-except-self/" },
    { "id": 36, "title": "Valid Sudoku", "difficulty": "Medium", "topic": "Arrays & Hashing", "url": "https://leetcode.com/problems/valid-sudoku/" },
    { "id": 128, "title": "Longest Consecutive Sequence", "difficulty": "Medium", "topic": "Arrays & Hashing", "url": "https://leetcode.com/problems/longest-consecutive-sequence/" },
    
    // --- TWO POINTERS ---
    { "id": 125, "title": "Valid Palindrome", "difficulty": "Easy", "topic": "Two Pointers", "url": "https://leetcode.com/problems/valid-palindrome/" },
    { "id": 167, "title": "Two Sum II", "difficulty": "Medium", "topic": "Two Pointers", "url": "https://leetcode.com/problems/two-sum-ii-input-array-is-sorted/" },
    { "id": 15, "title": "3Sum", "difficulty": "Medium", "topic": "Two Pointers", "url": "https://leetcode.com/problems/3sum/" },
    { "id": 11, "title": "Container With Most Water", "difficulty": "Medium", "topic": "Two Pointers", "url": "https://leetcode.com/problems/container-with-most-water/" },
    { "id": 42, "title": "Trapping Rain Water", "difficulty": "Hard", "topic": "Two Pointers", "url": "https://leetcode.com/problems/trapping-rain-water/" },

    // --- SLIDING WINDOW ---
    { "id": 121, "title": "Best Time to Buy and Sell Stock", "difficulty": "Easy", "topic": "Sliding Window", "url": "https://leetcode.com/problems/best-time-to-buy-and-sell-stock/" },
    { "id": 3, "title": "Longest Substring Without Repeating", "difficulty": "Medium", "topic": "Sliding Window", "url": "https://leetcode.com/problems/longest-substring-without-repeating-characters/" },
    { "id": 424, "title": "Longest Repeating Character Replacement", "difficulty": "Medium", "topic": "Sliding Window", "url": "https://leetcode.com/problems/longest-repeating-character-replacement/" },
    { "id": 76, "title": "Minimum Window Substring", "difficulty": "Hard", "topic": "Sliding Window", "url": "https://leetcode.com/problems/minimum-window-substring/" },

    // --- STACK ---
    { "id": 20, "title": "Valid Parentheses", "difficulty": "Easy", "topic": "Stack", "url": "https://leetcode.com/problems/valid-parentheses/" },
    { "id": 155, "title": "Min Stack", "difficulty": "Medium", "topic": "Stack", "url": "https://leetcode.com/problems/min-stack/" },
    { "id": 150, "title": "Evaluate Reverse Polish Notation", "difficulty": "Medium", "topic": "Stack", "url": "https://leetcode.com/problems/evaluate-reverse-polish-notation/" },
    { "id": 22, "title": "Generate Parentheses", "difficulty": "Medium", "topic": "Stack", "url": "https://leetcode.com/problems/generate-parentheses/" },
    { "id": 739, "title": "Daily Temperatures", "difficulty": "Medium", "topic": "Stack", "url": "https://leetcode.com/problems/daily-temperatures/" },
    { "id": 84, "title": "Largest Rectangle in Histogram", "difficulty": "Hard", "topic": "Stack", "url": "https://leetcode.com/problems/largest-rectangle-in-histogram/" },

    // --- BINARY SEARCH ---
    { "id": 704, "title": "Binary Search", "difficulty": "Easy", "topic": "Binary Search", "url": "https://leetcode.com/problems/binary-search/" },
    { "id": 74, "title": "Search a 2D Matrix", "difficulty": "Medium", "topic": "Binary Search", "url": "https://leetcode.com/problems/search-a-2d-matrix/" },
    { "id": 875, "title": "Koko Eating Bananas", "difficulty": "Medium", "topic": "Binary Search", "url": "https://leetcode.com/problems/koko-eating-bananas/" },
    { "id": 153, "title": "Find Minimum in Rotated Sorted Array", "difficulty": "Medium", "topic": "Binary Search", "url": "https://leetcode.com/problems/find-minimum-in-rotated-sorted-array/" },
    { "id": 33, "title": "Search in Rotated Sorted Array", "difficulty": "Medium", "topic": "Binary Search", "url": "https://leetcode.com/problems/search-in-rotated-sorted-array/" },
    { "id": 4, "title": "Median of Two Sorted Arrays", "difficulty": "Hard", "topic": "Binary Search", "url": "https://leetcode.com/problems/median-of-two-sorted-arrays/" },

    // --- LINKED LIST ---
    { "id": 206, "title": "Reverse Linked List", "difficulty": "Easy", "topic": "Linked List", "url": "https://leetcode.com/problems/reverse-linked-list/" },
    { "id": 21, "title": "Merge Two Sorted Lists", "difficulty": "Easy", "topic": "Linked List", "url": "https://leetcode.com/problems/merge-two-sorted-lists/" },
    { "id": 143, "title": "Reorder List", "difficulty": "Medium", "topic": "Linked List", "url": "https://leetcode.com/problems/reorder-list/" },
    { "id": 19, "title": "Remove Nth Node From End of List", "difficulty": "Medium", "topic": "Linked List", "url": "https://leetcode.com/problems/remove-nth-node-from-end-of-list/" },
    { "id": 141, "title": "Linked List Cycle", "difficulty": "Easy", "topic": "Linked List", "url": "https://leetcode.com/problems/linked-list-cycle/" },
    { "id": 23, "title": "Merge k Sorted Lists", "difficulty": "Hard", "topic": "Linked List", "url": "https://leetcode.com/problems/merge-k-sorted-lists/" },

    // --- TREES ---
    { "id": 226, "title": "Invert Binary Tree", "difficulty": "Easy", "topic": "Trees", "url": "https://leetcode.com/problems/invert-binary-tree/" },
    { "id": 104, "title": "Maximum Depth of Binary Tree", "difficulty": "Easy", "topic": "Trees", "url": "https://leetcode.com/problems/maximum-depth-of-binary-tree/" },
    { "id": 543, "title": "Diameter of Binary Tree", "difficulty": "Easy", "topic": "Trees", "url": "https://leetcode.com/problems/diameter-of-binary-tree/" },
    { "id": 110, "title": "Balanced Binary Tree", "difficulty": "Easy", "topic": "Trees", "url": "https://leetcode.com/problems/balanced-binary-tree/" },
    { "id": 100, "title": "Same Tree", "difficulty": "Easy", "topic": "Trees", "url": "https://leetcode.com/problems/same-tree/" },
    { "id": 102, "title": "Binary Tree Level Order Traversal", "difficulty": "Medium", "topic": "Trees", "url": "https://leetcode.com/problems/binary-tree-level-order-traversal/" },
    { "id": 98, "title": "Validate Binary Search Tree", "difficulty": "Medium", "topic": "Trees", "url": "https://leetcode.com/problems/validate-binary-search-tree/" },
    { "id": 230, "title": "Kth Smallest Element in a BST", "difficulty": "Medium", "topic": "Trees", "url": "https://leetcode.com/problems/kth-smallest-element-in-a-bst/" },
    { "id": 124, "title": "Binary Tree Maximum Path Sum", "difficulty": "Hard", "topic": "Trees", "url": "https://leetcode.com/problems/binary-tree-maximum-path-sum/" },

    // --- TRIES ---
    { "id": 208, "title": "Implement Trie (Prefix Tree)", "difficulty": "Medium", "topic": "Tries", "url": "https://leetcode.com/problems/implement-trie-prefix-tree/" },
    { "id": 211, "title": "Design Add and Search Words", "difficulty": "Medium", "topic": "Tries", "url": "https://leetcode.com/problems/design-add-and-search-words-data-structure/" },
    { "id": 212, "title": "Word Search II", "difficulty": "Hard", "topic": "Tries", "url": "https://leetcode.com/problems/word-search-ii/" },

    // --- HEAP ---
    { "id": 703, "title": "Kth Largest Element in a Stream", "difficulty": "Easy", "topic": "Heap", "url": "https://leetcode.com/problems/kth-largest-element-in-a-stream/" },
    { "id": 973, "title": "K Closest Points to Origin", "difficulty": "Medium", "topic": "Heap", "url": "https://leetcode.com/problems/k-closest-points-to-origin/" },
    { "id": 215, "title": "Kth Largest Element in an Array", "difficulty": "Medium", "topic": "Heap", "url": "https://leetcode.com/problems/kth-largest-element-in-an-array/" },
    { "id": 295, "title": "Find Median from Data Stream", "difficulty": "Hard", "topic": "Heap", "url": "https://leetcode.com/problems/find-median-from-data-stream/" },

    // --- BACKTRACKING ---
    { "id": 78, "title": "Subsets", "difficulty": "Medium", "topic": "Backtracking", "url": "https://leetcode.com/problems/subsets/" },
    { "id": 39, "title": "Combination Sum", "difficulty": "Medium", "topic": "Backtracking", "url": "https://leetcode.com/problems/combination-sum/" },
    { "id": 46, "title": "Permutations", "difficulty": "Medium", "topic": "Backtracking", "url": "https://leetcode.com/problems/permutations/" },
    { "id": 79, "title": "Word Search", "difficulty": "Medium", "topic": "Backtracking", "url": "https://leetcode.com/problems/word-search/" },
    { "id": 51, "title": "N-Queens", "difficulty": "Hard", "topic": "Backtracking", "url": "https://leetcode.com/problems/n-queens/" },

    // --- GRAPHS ---
    { "id": 200, "title": "Number of Islands", "difficulty": "Medium", "topic": "Graphs", "url": "https://leetcode.com/problems/number-of-islands/" },
    { "id": 695, "title": "Max Area of Island", "difficulty": "Medium", "topic": "Graphs", "url": "https://leetcode.com/problems/max-area-of-island/" },
    { "id": 133, "title": "Clone Graph", "difficulty": "Medium", "topic": "Graphs", "url": "https://leetcode.com/problems/clone-graph/" },
    { "id": 994, "title": "Rotting Oranges", "difficulty": "Medium", "topic": "Graphs", "url": "https://leetcode.com/problems/rotting-oranges/" },
    { "id": 207, "title": "Course Schedule", "difficulty": "Medium", "topic": "Graphs", "url": "https://leetcode.com/problems/course-schedule/" },
    { "id": 127, "title": "Word Ladder", "difficulty": "Hard", "topic": "Graphs", "url": "https://leetcode.com/problems/word-ladder/" },

    // --- ADVANCED GRAPHS ---
    { "id": 1584, "title": "Min Cost to Connect All Points", "difficulty": "Medium", "topic": "Advanced Graphs", "url": "https://leetcode.com/problems/min-cost-to-connect-all-points/" },
    { "id": 778, "title": "Swim in Rising Water", "difficulty": "Hard", "topic": "Advanced Graphs", "url": "https://leetcode.com/problems/swim-in-rising-water/" },

    // --- 1-D DYNAMIC PROGRAMMING ---
    { "id": 70, "title": "Climbing Stairs", "difficulty": "Easy", "topic": "1-D Dynamic Programming", "url": "https://leetcode.com/problems/climbing-stairs/" },
    { "id": 746, "title": "Min Cost Climbing Stairs", "difficulty": "Easy", "topic": "1-D Dynamic Programming", "url": "https://leetcode.com/problems/min-cost-climbing-stairs/" },
    { "id": 198, "title": "House Robber", "difficulty": "Medium", "topic": "1-D Dynamic Programming", "url": "https://leetcode.com/problems/house-robber/" },
    { "id": 213, "title": "House Robber II", "difficulty": "Medium", "topic": "1-D Dynamic Programming", "url": "https://leetcode.com/problems/house-robber-ii/" },
    { "id": 5, "title": "Longest Palindromic Substring", "difficulty": "Medium", "topic": "1-D Dynamic Programming", "url": "https://leetcode.com/problems/longest-palindromic-substring/" },
    { "id": 647, "title": "Palindromic Substrings", "difficulty": "Medium", "topic": "1-D Dynamic Programming", "url": "https://leetcode.com/problems/palindromic-substrings/" },
    { "id": 91, "title": "Decode Ways", "difficulty": "Medium", "topic": "1-D Dynamic Programming", "url": "https://leetcode.com/problems/decode-ways/" },
    { "id": 322, "title": "Coin Change", "difficulty": "Medium", "topic": "1-D Dynamic Programming", "url": "https://leetcode.com/problems/coin-change/" },
    { "id": 152, "title": "Maximum Product Subarray", "difficulty": "Medium", "topic": "1-D Dynamic Programming", "url": "https://leetcode.com/problems/maximum-product-subarray/" },
    { "id": 139, "title": "Word Break", "difficulty": "Medium", "topic": "1-D Dynamic Programming", "url": "https://leetcode.com/problems/word-break/" },
    { "id": 300, "title": "Longest Increasing Subsequence", "difficulty": "Medium", "topic": "1-D Dynamic Programming", "url": "https://leetcode.com/problems/longest-increasing-subsequence/" },

    // --- 2-D DYNAMIC PROGRAMMING ---
    { "id": 62, "title": "Unique Paths", "difficulty": "Medium", "topic": "2-D Dynamic Programming", "url": "https://leetcode.com/problems/unique-paths/" },
    { "id": 1143, "title": "Longest Common Subsequence", "difficulty": "Medium", "topic": "2-D Dynamic Programming", "url": "https://leetcode.com/problems/longest-common-subsequence/" },
    { "id": 309, "title": "Best Time to Buy/Sell Stock with Cooldown", "difficulty": "Medium", "topic": "2-D Dynamic Programming", "url": "https://leetcode.com/problems/best-time-to-buy-and-sell-stock-with-cooldown/" },
    { "id": 518, "title": "Coin Change II", "difficulty": "Medium", "topic": "2-D Dynamic Programming", "url": "https://leetcode.com/problems/coin-change-ii/" },
    { "id": 494, "title": "Target Sum", "difficulty": "Medium", "topic": "2-D Dynamic Programming", "url": "https://leetcode.com/problems/target-sum/" },
    { "id": 97, "title": "Interleaving String", "difficulty": "Medium", "topic": "2-D Dynamic Programming", "url": "https://leetcode.com/problems/interleaving-string/" },
    { "id": 329, "title": "Longest Increasing Path in a Matrix", "difficulty": "Hard", "topic": "2-D Dynamic Programming", "url": "https://leetcode.com/problems/longest-increasing-path-in-a-matrix/" },
    { "id": 115, "title": "Distinct Subsequences", "difficulty": "Hard", "topic": "2-D Dynamic Programming", "url": "https://leetcode.com/problems/distinct-subsequences/" },
    { "id": 72, "title": "Edit Distance", "difficulty": "Medium", "topic": "2-D Dynamic Programming", "url": "https://leetcode.com/problems/edit-distance/" },
    { "id": 10, "title": "Regular Expression Matching", "difficulty": "Hard", "topic": "2-D Dynamic Programming", "url": "https://leetcode.com/problems/regular-expression-matching/" },

    // --- GREEDY ---
    { "id": 53, "title": "Maximum Subarray", "difficulty": "Medium", "topic": "Greedy", "url": "https://leetcode.com/problems/maximum-subarray/" },
    { "id": 55, "title": "Jump Game", "difficulty": "Medium", "topic": "Greedy", "url": "https://leetcode.com/problems/jump-game/" },
    { "id": 134, "title": "Gas Station", "difficulty": "Medium", "topic": "Greedy", "url": "https://leetcode.com/problems/gas-station/" },
    { "id": 846, "title": "Hand of Straights", "difficulty": "Medium", "topic": "Greedy", "url": "https://leetcode.com/problems/hand-of-straights/" },
    { "id": 763, "title": "Partition Labels", "difficulty": "Medium", "topic": "Greedy", "url": "https://leetcode.com/problems/partition-labels/" },

    // --- INTERVALS ---
    { "id": 57, "title": "Insert Interval", "difficulty": "Medium", "topic": "Intervals", "url": "https://leetcode.com/problems/insert-interval/" },
    { "id": 56, "title": "Merge Intervals", "difficulty": "Medium", "topic": "Intervals", "url": "https://leetcode.com/problems/merge-intervals/" },
    { "id": 435, "title": "Non-overlapping Intervals", "difficulty": "Medium", "topic": "Intervals", "url": "https://leetcode.com/problems/non-overlapping-intervals/" },
    { "id": 252, "title": "Meeting Rooms", "difficulty": "Easy", "topic": "Intervals", "url": "https://leetcode.com/problems/meeting-rooms/" },
    { "id": 253, "title": "Meeting Rooms II", "difficulty": "Medium", "topic": "Intervals", "url": "https://leetcode.com/problems/meeting-rooms-ii/" },

    // --- MATH & GEOMETRY ---
    { "id": 48, "title": "Rotate Image", "difficulty": "Medium", "topic": "Math & Geometry", "url": "https://leetcode.com/problems/rotate-image/" },
    { "id": 73, "title": "Set Matrix Zeroes", "difficulty": "Medium", "topic": "Math & Geometry", "url": "https://leetcode.com/problems/set-matrix-zeroes/" },
    { "id": 202, "title": "Happy Number", "difficulty": "Easy", "topic": "Math & Geometry", "url": "https://leetcode.com/problems/happy-number/" },
    { "id": 66, "title": "Plus One", "difficulty": "Easy", "topic": "Math & Geometry", "url": "https://leetcode.com/problems/plus-one/" },
    { "id": 50, "title": "Pow(x, n)", "difficulty": "Medium", "topic": "Math & Geometry", "url": "https://leetcode.com/problems/powx-n/" },

    // --- BIT MANIPULATION ---
    { "id": 136, "title": "Single Number", "difficulty": "Easy", "topic": "Bit Manipulation", "url": "https://leetcode.com/problems/single-number/" },
    { "id": 191, "title": "Number of 1 Bits", "difficulty": "Easy", "topic": "Bit Manipulation", "url": "https://leetcode.com/problems/number-of-1-bits/" },
    { "id": 338, "title": "Counting Bits", "difficulty": "Easy", "topic": "Bit Manipulation", "url": "https://leetcode.com/problems/counting-bits/" },
    { "id": 190, "title": "Reverse Bits", "difficulty": "Easy", "topic": "Bit Manipulation", "url": "https://leetcode.com/problems/reverse-bits/" },
    { "id": 268, "title": "Missing Number", "difficulty": "Easy", "topic": "Bit Manipulation", "url": "https://leetcode.com/problems/missing-number/" },
    { "id": 371, "title": "Sum of Two Integers", "difficulty": "Medium", "topic": "Bit Manipulation", "url": "https://leetcode.com/problems/sum-of-two-integers/" },
    { "id": 7, "title": "Reverse Integer", "difficulty": "Medium", "topic": "Bit Manipulation", "url": "https://leetcode.com/problems/reverse-integer/" }
];