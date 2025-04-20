package main

import (
	"log"

	"github.com/hajimehoshi/ebiten/v2"
)

// Game represents the main game state
type Game struct{}

// Update is called every frame (typically 1/60[s])
func (g *Game) Update() error {
	return nil
}

// Draw is called every frame (typically 1/60[s])
func (g *Game) Draw(screen *ebiten.Image) {
	// 何も描画しないとウィンドウは黒いままになります
}

// Layout takes the outside size (e.g., the window size) and returns the game's logical screen size
func (g *Game) Layout(outsideWidth, outsideHeight int) (screenWidth, screenHeight int) {
	return 640, 480
}

func main() {
	// ウィンドウのタイトルを設定
	ebiten.SetWindowTitle("My First Ebitengine Game")
	// ウィンドウサイズを設定
	ebiten.SetWindowSize(640, 480)

	// ゲームを作成して実行
	game := &Game{}
	if err := ebiten.RunGame(game); err != nil {
		log.Fatal(err)
	}
}
