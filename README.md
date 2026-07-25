<!DOCTYPE html>

<html class="h-full" lang="en"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>Momo Video Maker - AI Interface</title>
<!-- Tailwind CSS v3 CDN -->
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<!-- Google Fonts: Inter -->
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;display=swap" rel="stylesheet"/>
<style data-purpose="custom-theme">
    body {
      font-family: 'Inter', sans-serif;
      background-color: #000000;
      color: #FFFFFF;
    }
    .panel-bg {
      background-color: #121214;
    }
    .sidebar-bg {
      background-color: #000000;
    }
    .accent-blue {
      background: linear-gradient(90deg, #A5CCF9 0%, #C4F1F9 100%);
      color: #000;
    }
    .selected-border {
      border: 2px solid #54A6FF;
    }
    /* Custom Scrollbar for dark theme */
    ::-webkit-scrollbar {
      width: 6px;
      height: 6px;
    }
    ::-webkit-scrollbar-track {
      background: transparent;
    }
    ::-webkit-scrollbar-thumb {
      background: #333;
      border-radius: 10px;
    }
    ::-webkit-scrollbar-thumb:hover {
      background: #444;
    }
  </style>
</head>
<body class="h-full flex overflow-hidden p-2 md:p-4">
<!-- BEGIN: Main Container (Outer Shell) -->
<div class="flex h-full w-full bg-black rounded-[32px] border border-zinc-800 overflow-hidden shadow-2xl">
<!-- BEGIN: Left Sidebar (Navigation) -->
<aside class="w-20 flex flex-none flex-col items-center py-6 border-r border-zinc-800" data-purpose="navigation-sidebar">
<!-- Logo -->
<div class="mb-10">
<div class="w-10 h-10 bg-[#121214] border border-zinc-700 rounded-xl flex items-center justify-center">
<span class="text-2xl font-bold text-white">M</span>
</div>
</div>
<!-- Nav Icons -->
<nav class="flex flex-col gap-8 flex-grow items-center text-zinc-500">
<div class="flex flex-col items-center gap-1 cursor-pointer hover:text-white transition-colors">
<svg class="h-6 w-6" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg>
<span class="text-[10px]">Home</span>
</div>
<div class="flex flex-col items-center gap-1 cursor-pointer hover:text-white transition-colors">
<svg class="h-6 w-6" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg>
<span class="text-[10px]">Projects</span>
</div>
<div class="flex flex-col items-center gap-1 cursor-pointer hover:text-white transition-colors">
<svg class="h-6 w-6" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg>
<span class="text-[10px]">Templates</span>
</div>
<div class="flex flex-col items-center gap-1 cursor-pointer hover:text-white transition-colors">
<svg class="h-6 w-6" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.175 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.382-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg>
<span class="text-[10px]">Starred</span>
</div>
<div class="flex flex-col items-center gap-1 cursor-pointer hover:text-white transition-colors">
<svg class="h-6 w-6" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10l4 4v10a2 2 0 01-2 2z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg>
<span class="text-[10px]">Blog</span>
</div>
</nav>
<!-- Bottom Sidebar Icons -->
<div class="flex flex-col gap-6 items-center text-zinc-500 mb-2">
<div class="cursor-pointer hover:text-white"><svg class="h-6 w-6" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path><path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg></div>
<div class="cursor-pointer hover:text-white"><svg class="h-6 w-6" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg></div>
<div class="w-8 h-8 rounded-full bg-indigo-500 overflow-hidden flex items-center justify-center">
<span class="text-xs">😊</span>
</div>
</div>
</aside>
<!-- END: Left Sidebar -->
<!-- BEGIN: Main Workspace Area -->
<main class="flex-grow flex flex-col h-full bg-[#000000] overflow-hidden" data-purpose="workspace-container">
<!-- BEGIN: Top Navigation Bar -->
<header class="h-16 flex items-center justify-between px-6 border-b border-zinc-800">
<div class="flex items-center gap-4">
<button class="p-2 hover:bg-zinc-800 rounded-lg transition-colors">
<svg class="h-5 w-5" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M10 19l-7-7m0 0l7-7m-7 7h18" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg>
</button>
<div class="flex items-center gap-1 cursor-pointer">
<span class="font-medium">First Project</span>
<svg class="h-4 w-4 text-zinc-400" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M19 9l-7 7-7-7" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg>
</div>
</div>
<div class="flex items-center gap-6">
<div class="flex items-center gap-6 text-zinc-400">
<button class="hover:text-white"><svg class="h-5 w-5" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg></button>
<button class="hover:text-white"><svg class="h-5 w-5" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg></button>
<button class="hover:text-white"><svg class="h-5 w-5" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg></button>
<button class="hover:text-white"><svg class="h-5 w-5" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg></button>
</div>
<div class="flex items-center gap-2">
<button class="p-2 bg-zinc-800 rounded-full hover:bg-zinc-700">
<svg class="h-5 w-5" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg>
</button>
<button class="accent-blue px-8 py-2 rounded-full font-bold text-sm shadow-lg hover:brightness-110 transition-all">Export</button>
</div>
</div>
</header>
<!-- END: Top Navigation Bar -->
<!-- BEGIN: Content Body (Three Panels) -->
<div class="flex flex-grow overflow-hidden p-4 gap-4">
<!-- BEGIN: Left Panel (Styles & Filters) -->
<section class="w-1/4 panel-bg rounded-[24px] p-5 flex flex-col gap-6 overflow-y-auto" data-purpose="style-panel">
<div class="relative">
<span class="absolute left-3 top-2.5 text-zinc-500">
<svg class="h-4 w-4" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg>
</span>
<input class="w-full bg-zinc-800 border-none rounded-xl py-2 pl-10 pr-4 text-sm focus:ring-1 focus:ring-zinc-600 placeholder-zinc-500" placeholder="Search" type="text"/>
</div>
<div>
<h3 class="text-zinc-300 text-sm font-semibold mb-4">Style</h3>
<div class="flex flex-col gap-1">
<button class="flex items-center justify-between p-2 rounded-lg hover:bg-zinc-800 text-sm text-zinc-400">
<span>Movie of the '90s</span>
</button>
<button class="flex items-center justify-between p-2 bg-zinc-800 rounded-lg text-sm text-white font-medium">
<span>Knitted World</span>
<span class="bg-blue-400 rounded-full p-0.5"><svg class="h-3 w-3 text-black" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M5 13l4 4L19 7" stroke-linecap="round" stroke-linejoin="round" stroke-width="3"></path></svg></span>
</button>
<button class="flex items-center justify-between p-2 rounded-lg hover:bg-zinc-800 text-sm text-zinc-400 text-left">
<span>Realistic 3D (Glossy)</span>
</button>
<button class="flex items-center justify-between p-2 rounded-lg hover:bg-zinc-800 text-sm text-zinc-400">
<span>2D Cartoon</span>
</button>
<button class="flex items-center justify-between p-2 rounded-lg hover:bg-zinc-800 text-sm text-zinc-400">
<span>Live Sketch</span>
</button>
</div>
</div>
<div>
<h3 class="text-zinc-300 text-sm font-semibold mb-4">Filters</h3>
<div class="grid grid-cols-2 gap-3">
<div class="aspect-square bg-zinc-800 rounded-xl overflow-hidden border-2 border-blue-400 relative">
<img alt="Filter Preview" class="w-full h-full object-cover blur-[2px] opacity-60" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBzmCNGy0Gj32Z-X6uki2SfgAh5BsXwFl4SXzJ_nuETIw0H4z3cizA1T2imcxCW21pcMdk0_Yj0dYiQgFERwr-kak0BV6aNDDaTrrNoQGOc3NNBrDG8nvuxOS7sMckJkAsQfX404d1MeUDKhveoRht6yjuig1OdHl9xUGpfb5PWZt4NLVfbhaJlXi2fFjONBl4u2d4Ri98l7oBi4j5U0tQMtRBDzksT5YHzbguJ3TTvs01om7_Q_Q4xWrmHCTyfhWISKhIF8lzh-_j7"/>
<div class="absolute inset-0 flex items-center justify-center">
<span class="bg-blue-400 rounded-full p-0.5"><svg class="h-3 w-3 text-black" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M5 13l4 4L19 7" stroke-linecap="round" stroke-linejoin="round" stroke-width="3"></path></svg></span>
</div>
</div>
<div class="aspect-square bg-zinc-800 rounded-xl overflow-hidden border border-zinc-700">
<img alt="Filter Preview" class="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBzmCNGy0Gj32Z-X6uki2SfgAh5BsXwFl4SXzJ_nuETIw0H4z3cizA1T2imcxCW21pcMdk0_Yj0dYiQgFERwr-kak0BV6aNDDaTrrNoQGOc3NNBrDG8nvuxOS7sMckJkAsQfX404d1MeUDKhveoRht6yjuig1OdHl9xUGpfb5PWZt4NLVfbhaJlXi2fFjONBl4u2d4Ri98l7oBi4j5U0tQMtRBDzksT5YHzbguJ3TTvs01om7_Q_Q4xWrmHCTyfhWISKhIF8lzh-_j7"/>
</div>
<div class="aspect-square bg-zinc-800 rounded-xl overflow-hidden border border-zinc-700">
<img alt="Filter Preview" class="w-full h-full object-cover saturate-50" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBzmCNGy0Gj32Z-X6uki2SfgAh5BsXwFl4SXzJ_nuETIw0H4z3cizA1T2imcxCW21pcMdk0_Yj0dYiQgFERwr-kak0BV6aNDDaTrrNoQGOc3NNBrDG8nvuxOS7sMckJkAsQfX404d1MeUDKhveoRht6yjuig1OdHl9xUGpfb5PWZt4NLVfbhaJlXi2fFjONBl4u2d4Ri98l7oBi4j5U0tQMtRBDzksT5YHzbguJ3TTvs01om7_Q_Q4xWrmHCTyfhWISKhIF8lzh-_j7"/>
</div>
<div class="aspect-square bg-zinc-800 rounded-xl overflow-hidden border border-zinc-700">
<img alt="Filter Preview" class="w-full h-full object-cover grayscale" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBzmCNGy0Gj32Z-X6uki2SfgAh5BsXwFl4SXzJ_nuETIw0H4z3cizA1T2imcxCW21pcMdk0_Yj0dYiQgFERwr-kak0BV6aNDDaTrrNoQGOc3NNBrDG8nvuxOS7sMckJkAsQfX404d1MeUDKhveoRht6yjuig1OdHl9xUGpfb5PWZt4NLVfbhaJlXi2fFjONBl4u2d4Ri98l7oBi4j5U0tQMtRBDzksT5YHzbguJ3TTvs01om7_Q_Q4xWrmHCTyfhWISKhIF8lzh-_j7"/>
</div>
</div>
</div>
</section>
<!-- END: Left Panel -->
<!-- BEGIN: Central Viewport -->
<section class="flex-grow flex items-center justify-center relative rounded-[24px] overflow-hidden" data-purpose="video-viewport">
<img alt="Video Preview" class="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBzmCNGy0Gj32Z-X6uki2SfgAh5BsXwFl4SXzJ_nuETIw0H4z3cizA1T2imcxCW21pcMdk0_Yj0dYiQgFERwr-kak0BV6aNDDaTrrNoQGOc3NNBrDG8nvuxOS7sMckJkAsQfX404d1MeUDKhveoRht6yjuig1OdHl9xUGpfb5PWZt4NLVfbhaJlXi2fFjONBl4u2d4Ri98l7oBi4j5U0tQMtRBDzksT5YHzbguJ3TTvs01om7_Q_Q4xWrmHCTyfhWISKhIF8lzh-_j7"/>
</section>
<!-- END: Central Viewport -->
<!-- BEGIN: Right Panel (Script & Format) -->
<section class="w-1/4 panel-bg rounded-[24px] p-5 flex flex-col gap-6 overflow-y-auto" data-purpose="controls-panel">
<div class="bg-zinc-800/50 p-1 rounded-full flex gap-1">
<button class="flex-1 py-2 text-sm text-zinc-400">Image</button>
<button class="flex-1 py-2 text-sm bg-zinc-700 rounded-full flex items-center justify-center gap-2">
<span class="bg-blue-400 rounded-full p-0.5"><svg class="h-2 w-2 text-black" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M5 13l4 4L19 7" stroke-linecap="round" stroke-linejoin="round" stroke-width="3"></path></svg></span>
              Make a Video
            </button>
</div>
<div class="flex-grow flex flex-col relative">
<textarea class="w-full h-32 bg-zinc-800/30 border-dashed border-2 border-zinc-700 rounded-2xl p-4 text-sm text-zinc-400 resize-none focus:ring-1 focus:ring-zinc-600 focus:border-zinc-500" placeholder="Type your script here..."></textarea>
<div class="absolute bottom-4 left-4 flex gap-2">
<button class="p-2 bg-zinc-800 rounded-lg text-zinc-400 hover:text-white"><svg class="h-4 w-4" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M12 4v16m8-8H4" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg></button>
<button class="p-2 bg-zinc-800 rounded-lg text-zinc-400 hover:text-white"><svg class="h-4 w-4" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg></button>
</div>
<button class="absolute bottom-4 right-4 p-2 bg-blue-400 rounded-full text-black hover:bg-blue-300">
<svg class="h-4 w-4" fill="currentColor" viewbox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z"></path></svg>
</button>
</div>
<div>
<h3 class="text-zinc-300 text-sm font-semibold mb-3">Format</h3>
<div class="grid grid-cols-4 gap-2">
<button class="py-2 text-xs bg-zinc-800 rounded-lg text-zinc-400 border border-transparent">9:16</button>
<button class="py-2 text-xs bg-zinc-800 rounded-lg text-zinc-400 border border-transparent">3:4</button>
<button class="py-2 text-xs bg-zinc-800 rounded-lg text-zinc-400 border border-transparent">1:1</button>
<button class="py-2 text-xs bg-zinc-800 rounded-lg text-white font-medium flex items-center justify-center gap-1 border border-zinc-600">4:3 <span class="bg-blue-400 rounded-full p-0.5"><svg class="h-2 w-2 text-black" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M5 13l4 4L19 7" stroke-linecap="round" stroke-linejoin="round" stroke-width="3"></path></svg></span></button>
</div>
</div>
<div>
<h3 class="text-zinc-300 text-sm font-semibold mb-3">Quality</h3>
<div class="bg-zinc-800 p-1 rounded-xl flex">
<button class="flex-1 py-1.5 text-xs text-zinc-400">720p</button>
<button class="flex-1 py-1.5 text-xs text-zinc-400">1080p</button>
<button class="flex-grow-[1.5] py-1.5 text-xs bg-zinc-700 rounded-lg text-white flex items-center justify-center gap-2">
<span class="bg-blue-400 rounded-full p-0.5"><svg class="h-2 w-2 text-black" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M5 13l4 4L19 7" stroke-linecap="round" stroke-linejoin="round" stroke-width="3"></path></svg></span>
                4K · Advanced
              </button>
</div>
</div>
</section>
<!-- END: Right Panel -->
</div>
<!-- END: Content Body -->
<!-- BEGIN: Bottom Timeline Panel -->
<section class="h-1/3 p-4 pt-0" data-purpose="timeline-panel">
<div class="panel-bg w-full h-full rounded-[24px] flex flex-col p-4 overflow-hidden relative">
<!-- Timeline Controls -->
<div class="flex items-center justify-between mb-4 px-4">
<div class="flex items-center gap-4 text-zinc-400">
<button class="hover:text-white"><svg class="h-5 w-5" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg></button>
<button class="hover:text-white"><svg class="h-5 w-5" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M21 10h-10a8 8 0 00-8 8v2m18-10l-6 6m6-6l-6-6" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg></button>
<button class="hover:text-white"><svg class="h-5 w-5" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M14.121 14.121L19 19m-7-7l7-7m-7 7l-2.879 2.879M12 12L9.121 9.121m0 5.758L5 19m0-14l4.121 4.121" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg></button>
</div>
<div class="flex items-center gap-6">
<button class="text-zinc-400 hover:text-white"><svg class="h-5 w-5" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg></button>
<button class="text-zinc-400 hover:text-white"><svg class="h-5 w-5" fill="currentColor" viewbox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path clip-rule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" fill-rule="evenodd"></path></svg></button>
<button class="w-10 h-10 bg-blue-300 rounded-full flex items-center justify-center text-black">
<svg class="h-6 w-6 ml-1" fill="currentColor" viewbox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path clip-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" fill-rule="evenodd"></path></svg>
</button>
<button class="text-zinc-400 hover:text-white"><svg class="h-5 w-5" fill="currentColor" viewbox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path clip-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" fill-rule="evenodd"></path></svg></button>
<button class="text-zinc-400 hover:text-white"><svg class="h-5 w-5" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg></button>
</div>
<div class="flex items-center gap-4 text-zinc-400">
<button class="hover:text-white"><svg class="h-5 w-5" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg></button>
<button class="hover:text-white"><svg class="h-5 w-5" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg></button>
<button class="hover:text-white text-xl">...</button>
</div>
</div>
<!-- Timeline Ruler -->
<div class="flex items-center text-[10px] text-zinc-500 mb-2 px-10 gap-0 overflow-hidden select-none">
<span class="flex-none w-16">0s</span>
<span class="flex-none w-16">5s</span>
<span class="flex-none w-16">10s</span>
<span class="flex-none w-16">15s</span>
<span class="flex-none w-16">20s</span>
<span class="flex-none w-16">25s</span>
<span class="flex-none w-16">30s</span>
<span class="flex-none w-16">35s</span>
<span class="flex-none w-16">40s</span>
<span class="flex-none w-16">45s</span>
<span class="flex-none w-16">50s</span>
<span class="flex-none w-16">55s</span>
<span class="flex-none w-16">60s</span>
<span class="flex-none w-16">65s</span>
<span class="flex-none w-16">70s</span>
<span class="flex-none w-16">75s</span>
<span class="flex-none w-16">80s</span>
</div>
<!-- Timeline Playhead Line -->
<div class="absolute top-[80px] bottom-16 left-[27.5%] w-0.5 bg-blue-400 z-10 before:content-[''] before:absolute before:-top-1.5 before:-left-1.5 before:w-4 before:h-4 before:bg-white before:rotate-45 before:rounded-sm shadow-[0_0_10px_rgba(59,130,246,0.5)]"></div>
<!-- Timeline Tracks -->
<div class="flex flex-col gap-3 px-4 relative flex-grow overflow-hidden">
<!-- Video Track -->
<div class="flex items-center gap-4">
<div class="w-6 h-6 text-zinc-500"><svg class="h-5 w-5" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg></div>
<div class="flex-grow flex gap-1 h-12">
<div class="w-1/4 h-full bg-zinc-800 rounded-lg overflow-hidden border border-zinc-700 flex">
<img class="h-full w-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBzmCNGy0Gj32Z-X6uki2SfgAh5BsXwFl4SXzJ_nuETIw0H4z3cizA1T2imcxCW21pcMdk0_Yj0dYiQgFERwr-kak0BV6aNDDaTrrNoQGOc3NNBrDG8nvuxOS7sMckJkAsQfX404d1MeUDKhveoRht6yjuig1OdHl9xUGpfb5PWZt4NLVfbhaJlXi2fFjONBl4u2d4Ri98l7oBi4j5U0tQMtRBDzksT5YHzbguJ3TTvs01om7_Q_Q4xWrmHCTyfhWISKhIF8lzh-_j7"/>
</div>
<div class="w-1/6 h-full bg-zinc-800 rounded-lg overflow-hidden border-2 border-blue-400 flex opacity-90">
<img class="h-full w-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBzmCNGy0Gj32Z-X6uki2SfgAh5BsXwFl4SXzJ_nuETIw0H4z3cizA1T2imcxCW21pcMdk0_Yj0dYiQgFERwr-kak0BV6aNDDaTrrNoQGOc3NNBrDG8nvuxOS7sMckJkAsQfX404d1MeUDKhveoRht6yjuig1OdHl9xUGpfb5PWZt4NLVfbhaJlXi2fFjONBl4u2d4Ri98l7oBi4j5U0tQMtRBDzksT5YHzbguJ3TTvs01om7_Q_Q4xWrmHCTyfhWISKhIF8lzh-_j7"/>
</div>
<div class="w-1/3 h-full bg-zinc-800 rounded-lg overflow-hidden border border-zinc-700 flex">
<img class="h-full w-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBzmCNGy0Gj32Z-X6uki2SfgAh5BsXwFl4SXzJ_nuETIw0H4z3cizA1T2imcxCW21pcMdk0_Yj0dYiQgFERwr-kak0BV6aNDDaTrrNoQGOc3NNBrDG8nvuxOS7sMckJkAsQfX404d1MeUDKhveoRht6yjuig1OdHl9xUGpfb5PWZt4NLVfbhaJlXi2fFjONBl4u2d4Ri98l7oBi4j5U0tQMtRBDzksT5YHzbguJ3TTvs01om7_Q_Q4xWrmHCTyfhWISKhIF8lzh-_j7"/>
</div>
</div>
<button class="w-8 h-8 bg-zinc-800 rounded-full flex items-center justify-center text-zinc-500 hover:text-white">
<svg class="h-5 w-5" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M12 4v16m8-8H4" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg>
</button>
</div>
<!-- Audio Track -->
<div class="flex items-center gap-4">
<div class="w-6 h-6 text-zinc-500"><svg class="h-5 w-5" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg></div>
<div class="flex-grow flex gap-2 h-10">
<div class="w-1/5 h-full bg-zinc-900 border border-zinc-800 rounded-lg relative overflow-hidden">
<svg class="absolute inset-0 w-full h-full text-zinc-700 opacity-50" preserveaspectratio="none"><path d="M0 20 L10 10 L20 25 L30 15 L40 30 L50 10 L60 20 L70 5 L80 25 L90 10 L100 20" fill="none" stroke="currentColor" stroke-width="1"></path></svg>
</div>
<div class="w-1/4 h-full bg-zinc-900 border-2 border-blue-400 rounded-lg relative overflow-hidden">
<svg class="absolute inset-0 w-full h-full text-blue-400 opacity-60" preserveaspectratio="none"><path d="M0 20 L10 5 L20 25 L30 10 L40 15 L50 5 L60 25 L70 15 L80 10 L90 20 L100 5" fill="none" stroke="currentColor" stroke-width="1"></path></svg>
</div>
<div class="w-1/2 h-full bg-zinc-900 border border-zinc-800 rounded-lg relative overflow-hidden">
<svg class="absolute inset-0 w-full h-full text-zinc-700 opacity-50" preserveaspectratio="none"><path d="M0 20 L10 15 L20 10 L30 25 L40 10 L50 20 L60 15 L70 25 L80 10 L90 20 L100 15 L110 5 L120 20 L130 10 L140 25" fill="none" stroke="currentColor" stroke-width="1"></path></svg>
</div>
</div>
<button class="w-8 h-8 bg-zinc-800 rounded-full flex items-center justify-center text-zinc-500 hover:text-white">
<svg class="h-5 w-5" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M12 4v16m8-8H4" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg>
</button>
</div>
<!-- Effect/Text Track -->
<div class="flex items-center gap-4">
<div class="w-6 h-6 text-zinc-500"><svg class="h-5 w-5" fill="none" stroke="currentColor" viewbox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg></div>
<div class="flex-grow flex gap-4 h-10 items-center">
<div class="px-4 py-1.5 bg-zinc-800 border border-zinc-700 rounded-full flex items-center gap-2">
<span class="text-[10px] text-zinc-500 font-bold uppercase">Text</span>
<span class="text-xs text-zinc-300">Wow! It's wonderful!</span>
</div>
<div class="px-4 py-1.5 bg-blue-900/30 border border-blue-500 rounded-full flex items-center gap-2">
<span class="text-[10px] text-blue-400 font-bold uppercase">Effect</span>
<span class="text-xs text-zinc-200">Gaussian Blur</span>
</div>
<div class="px-4 py-1.5 bg-zinc-800 border border-zinc-700 rounded-full flex items-center gap-2">
<span class="text-[10px] text-zinc-500 font-bold uppercase">Filter</span>
<span class="text-xs text-zinc-300">Bright Summer</span>
</div>
</div>
</div>
</div>
</div>
</section>
<!-- END: Bottom Timeline Panel -->
</main>
<!-- END: Main Workspace -->
</div>
<!-- END: Main Container -->
</body></html>