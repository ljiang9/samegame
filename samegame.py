#!/usr/bin/env python3
"""SameGame（Clickomania 消消乐）——终端版。

规则：
- 棋盘默认 10 行 × 15 列，5 种颜色。
- 点击（选择）一组 2 个以上上下左右相连的同色格子即可消除。
- 消除后：上方格子下落填补；空列向左塌陷。
- 得分：消除 n 个得 (n-2)^2 分；清空整盘额外 +1000 分。
- 无组可消时结束。

纯标准库：argparse / copy / random / sys。
"""

import argparse
import copy
import random
import sys

ROWS = 10
COLS = 15
NCOLORS = 5
CLEAR_BONUS = 1000
GLYPHS = "ABCDE"  # 终端友好的字母表示；颜色数<=5 时可用


class IllegalMove(Exception):
    """非法走法。"""


class SameGame:
    def __init__(self, rows=ROWS, cols=COLS, colors=NCOLORS, rng=None, board=None):
        self.rows = rows
        self.cols = cols
        self.colors = colors
        self.rng = rng or random.Random()
        if board is not None:
            self.board = copy.deepcopy(board)
        else:
            self.board = [
                [self.rng.randrange(colors) for _ in range(cols)]
                for _ in range(rows)
            ]
        self.score = 0
        self.moves = 0
        self.cleared = False

    # ---------- 核心规则 ----------

    def groups(self):
        """返回所有可消除的组（>=2 个相连同色），按大小降序。"""
        seen = [[False] * self.cols for _ in range(self.rows)]
        out = []
        for r in range(self.rows):
            for c in range(self.cols):
                if self.board[r][c] is None or seen[r][c]:
                    continue
                color = self.board[r][c]
                stack = [(r, c)]
                seen[r][c] = True
                cells = []
                while stack:
                    cr, cc = stack.pop()
                    cells.append((cr, cc))
                    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nr, nc = cr + dr, cc + dc
                        if (0 <= nr < self.rows and 0 <= nc < self.cols
                                and not seen[nr][nc]
                                and self.board[nr][nc] == color):
                            seen[nr][nc] = True
                            stack.append((nr, nc))
                if len(cells) >= 2:
                    out.append({"color": color, "cells": cells, "size": len(cells)})
        out.sort(key=lambda g: -g["size"])
        return out

    @staticmethod
    def group_score(n):
        return (n - 2) ** 2

    def group_at(self, r, c):
        """(r, c) 所在的组；没有则返回 None。"""
        if not (0 <= r < self.rows and 0 <= c < self.cols):
            return None
        for g in self.groups():
            if (r, c) in g["cells"]:
                return g
        return None

    def play(self, r, c):
        """消除 (r, c) 所在的组。非法抛 IllegalMove。"""
        g = self.group_at(r, c)
        if g is None:
            raise IllegalMove("该格没有可消除的组（需要 2 个以上相连同色）")
        for cr, cc in g["cells"]:
            self.board[cr][cc] = None
        self.score += self.group_score(g["size"])
        self.moves += 1
        self._gravity()
        if self.is_clear():
            self.score += CLEAR_BONUS
            self.cleared = True
        return g["size"]

    def _gravity(self):
        """下落 + 空列左塌。"""
        for c in range(self.cols):
            stack = [self.board[r][c] for r in range(self.rows)
                     if self.board[r][c] is not None]
            for r in range(self.rows - 1, -1, -1):
                self.board[r][c] = stack.pop() if stack else None
        nonempty = [c for c in range(self.cols)
                    if any(self.board[r][c] is not None for r in range(self.rows))]
        new = [[None] * self.cols for _ in range(self.rows)]
        for nc, c in enumerate(nonempty):
            for r in range(self.rows):
                new[r][nc] = self.board[r][c]
        self.board = new

    def is_clear(self):
        return all(self.board[r][c] is None
                   for r in range(self.rows) for c in range(self.cols))

    def remaining_colors(self):
        return {self.board[r][c] for r in range(self.rows)
                for c in range(self.cols) if self.board[r][c] is not None}

    # ---------- 展示 ----------

    def render(self):
        lines = []
        head = "   " + " ".join(f"{c:>2}" for c in range(self.cols))
        lines.append(head)
        for r in range(self.rows):
            row = []
            for c in range(self.cols):
                v = self.board[r][c]
                row.append(" ." if v is None else f" {GLYPHS[v]}")
            lines.append(f"{r:>2} " + "".join(row))
        lines.append(f"得分 {self.score}  手数 {self.moves}")
        return "\n".join(lines)


# ---------- AI ----------

def greedy_move(game, rng):
    """1 步贪心：选最大的组；并列时优先能消光某种颜色的。"""
    groups = game.groups()
    if not groups:
        return None
    before = game.remaining_colors()
    best = None
    best_key = None
    for g in groups:
        after = set(before)
        after.discard(g["color"])
        empties_color = len(after) < len(before)
        key = (g["size"], 1 if empties_color else 0)
        if best_key is None or key > best_key:
            best_key = key
            best = g
    if best is None:
        return None
    return best["cells"][0]


def play_auto(rows, cols, colors, rng, verbose=False):
    game = SameGame(rows=rows, cols=cols, colors=colors, rng=rng)
    while True:
        mv = greedy_move(game, rng)
        if mv is None:
            break
        game.play(*mv)
        if verbose:
            print(game.render())
            print()
    return game


# ---------- CLI ----------

def play_interactive(rows, cols, colors, seed):
    rng = random.Random(seed) if seed is not None else random.Random()
    game = SameGame(rows=rows, cols=cols, colors=colors, rng=rng)
    print("=== SameGame 消消乐 ===")
    print("输入组编号消除，或输入「行 列」坐标；q 退出。")
    print("消除 n 个得 (n-2)^2 分，清空整盘 +1000。\n")
    while True:
        print(game.render())
        groups = game.groups()
        if not groups:
            print(f"\n无组可消，游戏结束！最终得分 {game.score}"
                  + ("（清空整盘！）" if game.cleared else ""))
            break
        print(f"\n可消除的组（共 {len(groups)} 组）：")
        for i, g in enumerate(groups[:20]):
            r0, c0 = g["cells"][0]
            print(f"  [{i}] 颜色{GLYPHS[g['color']]} 大小{g['size']}"
                  f" 得分+{SameGame.group_score(g['size'])}"
                  f"（如含 ({r0},{c0})）")
        if len(groups) > 20:
            print(f"  …还有 {len(groups) - 20} 组未列出，可用坐标选择")
        try:
            s = input("你的选择> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已退出。")
            break
        if s.lower() in ("q", "quit", "退出"):
            print("已退出。")
            break
        try:
            if " " in s:
                r, c = (int(x) for x in s.split())
                if game.group_at(r, c) is None:
                    raise IllegalMove("该坐标没有可消除的组")
                n = game.play(r, c)
            else:
                i = int(s)
                if not (0 <= i < len(groups)):
                    raise IllegalMove("编号超出范围")
                r, c = groups[i]["cells"][0]
                n = game.play(r, c)
            print(f"消除了 {n} 个，+{SameGame.group_score(n)} 分\n")
        except (ValueError, IllegalMove) as e:
            print(f"非法输入：{e}\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description="SameGame 消消乐（终端版）")
    ap.add_argument("--auto", action="store_true", help="AI 自动演示")
    ap.add_argument("--games", type=int, default=10, help="自动演示局数")
    ap.add_argument("--seed", type=int, default=None, help="随机种子")
    ap.add_argument("--rows", type=int, default=ROWS)
    ap.add_argument("--cols", type=int, default=COLS)
    ap.add_argument("--colors", type=int, default=NCOLORS)
    ap.add_argument("--verbose", action="store_true", help="打印每步棋盘")
    args = ap.parse_args(argv)

    if args.auto:
        rng = random.Random(args.seed)
        scores = []
        clears = 0
        for i in range(args.games):
            g = play_auto(args.rows, args.cols, args.colors, rng,
                          verbose=args.verbose)
            scores.append(g.score)
            clears += 1 if g.cleared else 0
            print(f"第 {i + 1}/{args.games} 局：得分 {g.score}"
                  f"（{g.moves} 手）"
                  + (" 清空整盘！" if g.cleared else ""))
        avg = sum(scores) / len(scores)
        print(f"\n共 {args.games} 局：平均 {avg:.1f} 分，"
              f"最高 {max(scores)} 分，清空 {clears} 局")
        return 0

    if not sys.stdin.isatty():
        print("交互模式需要终端；非终端请用 --auto 自动演示。", file=sys.stderr)
        return 2
    play_interactive(args.rows, args.cols, args.colors, args.seed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
