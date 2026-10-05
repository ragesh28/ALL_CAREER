export interface Top150Problem {
  id: number;
  title: string;
  difficulty: 'Easy' | 'Medium' | 'Hard';
  topic: string;
  url: string;
}

export const top150Data: Top150Problem[] = [
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
  { "id": 124, "title": "Binary Tree Maximum Path Sum", "difficulty": "Hard", "topic": "Trees", "url": "https://leetcode.com/problems/binary-tree-maximum-path-sum/" }
];
