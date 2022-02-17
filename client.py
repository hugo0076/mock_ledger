# import pygame
import random

width = 500
height = 500
# win = pygame.display.set_mode((width, height))
# pygame.display.set_caption("Client")
import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
clientNumber = 0


class Player:
    def __init__(self, x, y, width, height, color):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = color
        self.rect = (x, y, width, height)
        self.vel = 3

    def draw(self):
        print(f"color = {self.color}, rect = {self.rect}")
        # pygame.draw.rect(win, self.color, self.rect)

    def move(self):
        i = round(4 * random.random())
        if i == 2:
            self.x += self.vel
        if i == 3:
            self.x -= self.vel
        # keys = pygame.key.get_pressed()
        #
        # if keys[pygame.K_LEFT]:
        #    self.x -= self.vel
        #
        # if keys[pygame.K_RIGHT]:
        #    self.x += self.vel
        #
        # if keys[pygame.K_UP]:
        #    self.y -= self.vel
        #
        # if keys[pygame.K_DOWN]:
        #    self.y += self.vel

        self.rect = (self.x, self.y, self.width, self.height)


def redrawWindow(player):
    print("drawing")
    # win.fill((255,255,255))
    player.draw()
    # pygame.display.update()


def main():
    run = True
    p = Player(50, 50, 100, 100, (0, 255, 0))
    # clock = pygame.time.Clock()

    while run:
        # clock.tick(60)
        # for event in pygame.event.get():
        #    if event.type == pygame.QUIT:
        #        run = False
        #        pygame.quit()

        p.move()
        redrawWindow(p)


main()
