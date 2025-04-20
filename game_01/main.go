package main

import (
	"fmt"
	"image"
	"image/color"
	_ "image/png" // PNGファイルを読み込むために必要
	"log"
	"math"
	"math/rand"
	"os"

	"github.com/hajimehoshi/ebiten/v2"
	"github.com/hajimehoshi/ebiten/v2/text"
	"golang.org/x/image/font"
	"golang.org/x/image/font/basicfont"
)

// Game represents the main game state
type Game struct {
	gravelTexture *ebiten.Image
	rotation_rate float64   // 回転率を制御する変数
	fontFace      font.Face // テキスト描画用のフォント
}

// アルファグラデーションマスクを作成する関数
func createAlphaGradientMask(width, height int) *ebiten.Image {
	// 中心座標を計算
	centerX := float64(width) / 2
	centerY := float64(height) / 2

	// 完全不透明にする中心からの距離（画像の短辺の1/3程度）
	solidRadius := math.Min(float64(width), float64(height)) / 3

	// 透明になり始める位置から完全に透明になるまでの距離
	falloffDistance := math.Min(float64(width), float64(height)) / 20

	// ピクセルデータを一時的に格納するスライスを作成
	pixels := make([]byte, width*height*4)

	// ピクセルごとにアルファ値を計算
	for y := 0; y < height; y++ {
		for x := 0; x < width; x++ {
			// 中心からの距離を計算
			dx := float64(x) - centerX
			dy := float64(y) - centerY
			distance := math.Sqrt(dx*dx + dy*dy)

			// アルファ値の計算
			var alpha float64
			if distance <= solidRadius {
				// 一定距離内は完全不透明
				alpha = 1.0
			} else {
				// 一定距離を超えたら急激に透明になる
				// 距離に応じて1.0から0.0に線形に減少
				alpha = math.Max(0, 1.0-(distance-solidRadius)/falloffDistance)
			}

			// アルファ値の範囲を[0, 1]から[0, 255]に変換
			alphaInt := uint8(alpha * 255)

			// ピクセルデータの対応する位置に値を設定（RGBA）
			i := (y*width + x) * 4
			pixels[i] = 255        // R
			pixels[i+1] = 255      // G
			pixels[i+2] = 255      // B
			pixels[i+3] = alphaInt // A
		}
	}

	// ピクセルデータから画像を作成
	img := image.NewRGBA(image.Rect(0, 0, width, height))
	copy(img.Pix, pixels)
	maskImg := ebiten.NewImageFromImage(img)

	return maskImg
}

// テクスチャにアルファマスクを適用する関数
func applyAlphaMask(texture, mask *ebiten.Image) *ebiten.Image {
	w, h := texture.Size()
	result := ebiten.NewImage(w, h)

	// 元のテクスチャを描画
	result.DrawImage(texture, &ebiten.DrawImageOptions{})

	// マスクを適用（マスクのアルファチャネルが元画像のアルファチャネルを制御）
	op := &ebiten.DrawImageOptions{}
	op.CompositeMode = ebiten.CompositeModeDestinationIn
	result.DrawImage(mask, op)

	return result
}

// テクスチャファイルを読み込み、アルファチャネルを適用する関数
func loadTextureWithAlphaGradient(path string) (*ebiten.Image, error) {
	// 元のテクスチャを読み込む
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	img, _, err := image.Decode(f)
	if err != nil {
		return nil, err
	}

	texture := ebiten.NewImageFromImage(img)
	w, h := texture.Size()

	// アルファグラデーションマスクを作成
	mask := createAlphaGradientMask(w, h)

	// 改良した関数を使って、テクスチャにマスクを適用
	return applyAlphaMask(texture, mask), nil
}

// Update is called every frame (typically 1/60[s])
func (g *Game) Update() error {
	// キー入力で回転率を調整
	if ebiten.IsKeyPressed(ebiten.KeyRight) {
		// 右キーで少しずつ増加 (+0.01)
		g.rotation_rate += 0.001
	}
	if ebiten.IsKeyPressed(ebiten.KeyLeft) {
		// 左キーで少しずつ減少 (-0.01)
		g.rotation_rate -= 0.001
	}
	if ebiten.IsKeyPressed(ebiten.KeyUp) {
		// 上キーで大きく増加 (+0.1)
		g.rotation_rate += 0.01
	}
	if ebiten.IsKeyPressed(ebiten.KeyDown) {
		// 下キーで大きく減少 (-0.1)
		g.rotation_rate -= 0.01
	}
	// 回転率を0～3の範囲に制限
	if g.rotation_rate < 0 {
		g.rotation_rate = 0
	}
	if g.rotation_rate > 3 {
		g.rotation_rate = 3
	}

	return nil
}

// Draw is called every frame (typically 1/60[s])
func (g *Game) Draw(screen *ebiten.Image) {
	originalW, originalH := g.gravelTexture.Size()

	// タイルサイズを1/2に縮小することで、繰り返し回数を2倍にする
	w := originalW / 2
	h := originalH / 2

	screenW, screenH := screen.Size()

	// 画面を埋めるために必要な繰り返し回数を計算
	tilesX := (screenW+w-1)/w + 1 // +1を追加して画面端の処理を改善
	tilesY := (screenH + h - 1) / h

	// テクスチャを繰り返し描画
	for y := -1; y < tilesY; y++ {
		// 奇数行は0.5タイル分横にずらす
		offsetX := 0.0
		if y%2 == 1 {
			offsetX = float64(w) / 2
		}

		for x := -1; x < tilesX; x++ { // -1から開始して左端のタイルも描画
			op := &ebiten.DrawImageOptions{}

			// 疑似乱数を生成するための値（決定論的な値）
			// タイルの位置に基づく固定値を使って、同じタイルが常に同じ角度を持つようにします
			// x と y 値に基づいたシードを作成（同じ位置のタイルは常に同じランダム値を持つ）
			r := rand.New(rand.NewSource(int64(y*10000 + x)))

			// 回転角度を計算（0～2π範囲） - rotation_rateを乗算
			rotation := (r.Float64() - 0.5) * 2 * 2 * math.Pi * g.rotation_rate

			// 回転の中心をテクスチャの中央に設定
			op.GeoM.Translate(-float64(originalW)/2, -float64(originalH)/2)
			op.GeoM.Rotate(rotation)
			op.GeoM.Translate(float64(originalW)/2, float64(originalH)/2)

			op.GeoM.Translate(float64(x*w)+offsetX, float64(y*h))

			screen.DrawImage(g.gravelTexture, op)
		}
	}

	// rotation_rateの値を画面に表示
	msg := fmt.Sprintf("Rotation Rate: %.2f", g.rotation_rate)
	text.Draw(screen, msg, g.fontFace, 10, 25, color.White)

	// 操作方法を表示
	controls := "Controls: ←→ Small changes | ↑↓ Large changes"
	text.Draw(screen, controls, g.fontFace, 10, screenH-10, color.White)
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

	// 乱数の初期化は不要 (Go 1.20以降では自動的に初期化される)
	// rand.Seed は Go 1.20 で非推奨となっています

	// ゲームを作成
	game := &Game{
		rotation_rate: 1.0,                // 回転率の初期値を設定
		fontFace:      basicfont.Face7x13, // 基本フォントを使用
	}

	// アルファグラデーションを適用したテクスチャを読み込み
	var err error
	game.gravelTexture, err = loadTextureWithAlphaGradient("assets/textures/gravel_texture_1.png")
	if err != nil {
		log.Fatalf("テクスチャの読み込みに失敗しました: %v", err)
	}

	// ゲームを実行
	if err := ebiten.RunGame(game); err != nil {
		log.Fatal(err)
	}
}
