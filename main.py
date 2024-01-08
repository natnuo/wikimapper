from bs4 import BeautifulSoup
import requests
import math
import pygame
from pygame.locals import *
from pygame.time import *

def getPageUrl(page: str) -> str:
  return f"https://en.wikipedia.org/wiki/{page}"

def getPageFromUrl(url: str) -> str | None:
  s: str = url.split("/")
  # FUTURE: add compatibility for portals and stuff
  if (
    len(s) <= 1 or
    s[1] != "wiki" or
    "File:" in s[-1] or
    "Wikipedia:" in s[-1] or
    "Help:" in s[-1] or
    "Special:" in s[-1] or
    "Portal:" in s[-1] or 
    "Talk:" in s[-1] or 
    "Category:" in s[-1] or 
    "intitle:" in s[-1]
  ):
    return None
  return s[-1].split("#")[0]
  

def getConns(page: str, limit: int | None=None) -> set[str]:
  print(f"LOG: reading {page}")
  url: str = getPageUrl(page)
  page_content: bytes = requests.get(url).content
  soup: BeautifulSoup = BeautifulSoup(page_content, "lxml")
  res: set[str] = set()
  for link in soup("a"):
    if limit is not None and len(res) >= limit: break
    href: str | None = link.get("href")
    if href is not None:
      conn: str | None = getPageFromUrl(href)
      # wow another if statement this code is so neat /s
      # FUTURE: maybe remove conn != page if we want to allow showing connections to self,
      # though doing so would probably have little value bc don't almost all articles link to self
      # in the table of contents or smth
      if conn is not None and conn != page:
        res.add(conn)
  return res

class Node:
  def __init__(self, conns: set[str], page: str) -> None:
    self.conns: set[str] = conns
    self.page: str = page
    # 0, 0 is center
    self.x: int = None
    self.y: int = None
    self.size: int = 1
  
  def __str__(self) -> str:
    return (
f"""
Node::{self.page}
  {len(self.conns)} conns: [{self.conns}]
""")

# ew global variable
node_lookup: dict[str, Node] = {}

def buildNodes(page: str, depth: int, limit: int | None=None) -> None:
  global node_lookup

  if page in node_lookup.keys(): return
  
  n = Node(getConns(page, limit), page) if depth > 0 else Node(set(), page)
  depth -= 1
  node_lookup[page] = n
  for p in n.conns: buildNodes(p, depth, limit)

def positionNodes(root: Node, depth: int, d_factor: float, size_factor: float, x:int=0, y:int=0) -> None:
  root.size = max(size_factor * (2 ** (depth / 2)), root.size)
  if root.x is not None: return
  root.x = x
  root.y = y
  if len(root.conns) == 0: return
  global node_lookup
  l: float = d_factor ** depth
  theta_min: float = math.radians(360 / len(root.conns))
  depth -= 1
  for i, n in enumerate(root.conns):
    positionNodes(node_lookup[n], depth-1, d_factor, size_factor, math.floor(math.cos(theta_min * i) * l + x), math.floor(math.sin(theta_min * i) * l + y))

def getTopLeftDrawCoord(node: Node, scaling_factor: float, WINDOW_SIZE: tuple[int], x_offset: float, y_offset: float) -> tuple[int]:
  return (math.floor(node.x * scaling_factor) + (WINDOW_SIZE[0] // 2) + math.floor(x_offset * scaling_factor), math.floor(node.y * scaling_factor) + (WINDOW_SIZE[1] // 2) + math.floor(y_offset * scaling_factor))

WINDOW_SIZE: tuple[int, int] = (555, 555)  # x, y
ROOT_PAGE: str = "Wikipedia"
DEPTH: int = 3
PAGE_CONN_LIMIT: int = 10
NODE_DISTANCE_FACTOR: float = 3
MARGIN: int = 10
scaling_factor: float = (min(WINDOW_SIZE) - MARGIN - 10) / (NODE_DISTANCE_FACTOR ** DEPTH) / 2
CONNECTION_LINE_WIDTH_FACTOR: float = NODE_DISTANCE_FACTOR * 0.0000069 * scaling_factor
CAMERA_MVMT_SPEED_FACTOR: float = 33
CAMERA_MVMT_MOMENTUM_FACTOR: float = 0.92
NODE_SIZE_FACTOR: float = NODE_DISTANCE_FACTOR * 0.22 * scaling_factor
buildNodes(ROOT_PAGE, DEPTH, PAGE_CONN_LIMIT)
positionNodes(node_lookup[ROOT_PAGE], DEPTH, NODE_DISTANCE_FACTOR, NODE_SIZE_FACTOR)

pygame.init()
window = pygame.display.set_mode(WINDOW_SIZE)

# FUTURE: ADD MOMENTUM TO MOVEMENT
# FUTURE: FIX ZOOM ANCHOR POINT
v_x: float = 0
v_y: float = 0
x_offset: float = 0
y_offset: float = 0
clock = pygame.time.Clock()
run: bool = True
while run:
  clock.tick(60)  # set framerate
  window.fill((0, 0, 0))
  for page, node in node_lookup.items():
    n_dpos: tuple[int] = getTopLeftDrawCoord(node, scaling_factor, WINDOW_SIZE, x_offset, y_offset)
    s: int = math.floor(max(node.size, 1))
    # draw_offset: int = (node.size / scaling_factor) // 2
    pygame.draw.circle(window, (255, 255, 255), n_dpos, s)
    for conn in node.conns:
      pygame.draw.line(
        window, (255, 255, 255), n_dpos,
        getTopLeftDrawCoord(node_lookup[conn], scaling_factor, WINDOW_SIZE, x_offset, y_offset),
        math.floor(max(CONNECTION_LINE_WIDTH_FACTOR * scaling_factor, 1))
      )
      
  pygame.display.update()
  pressed_keys = pygame.key.get_pressed()
  mvmt_spd: float = CAMERA_MVMT_SPEED_FACTOR / scaling_factor
  # FUTURE: add faster movement if smth like ctrl is pressed
  tgt_v_x: float = 0
  tgt_v_y: float = 0
  if pressed_keys[K_w]:
    tgt_v_y = mvmt_spd
  if pressed_keys[K_a]:
    tgt_v_x = mvmt_spd
  if pressed_keys[K_s]:
    tgt_v_y = -mvmt_spd
  if pressed_keys[K_d]:
    tgt_v_x = -mvmt_spd
  if pressed_keys[K_LCTRL]:
    tgt_v_x *= 2
    tgt_v_y *= 2
  v_x = (CAMERA_MVMT_MOMENTUM_FACTOR * v_x + (1-CAMERA_MVMT_MOMENTUM_FACTOR) * tgt_v_x) if (abs(v_x) > 0.11 or tgt_v_x != 0) else 0
  v_y = (CAMERA_MVMT_MOMENTUM_FACTOR * v_y + (1-CAMERA_MVMT_MOMENTUM_FACTOR) * tgt_v_y) if (abs(v_y) > 0.11 or tgt_v_y != 0) else 0
  x_offset += v_x
  y_offset += v_y
  for event in pygame.event.get():
    if event.type == pygame.MOUSEBUTTONDOWN:
      if event.button == 4: scaling_factor *= 1.1
      if event.button == 5: scaling_factor /= 1.1
    elif event.type == pygame.QUIT:
        run = False

pygame.quit()
exit()