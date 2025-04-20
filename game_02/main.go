package main

import (
	"fmt"
	"image/color"
	"log"
	"math"

	"github.com/hajimehoshi/ebiten/v2"
	"github.com/hajimehoshi/ebiten/v2/ebitenutil"
	"github.com/hajimehoshi/ebiten/v2/inpututil"
)

// QWERTY配列における各キーの相対座標
// TYGHの中心を原点(0,0)として定義
var keyPositions = map[ebiten.Key]struct{ X, Y float64 }{
	// 数字キー（最上段）
	ebiten.Key1: {-5.5, -2.5},
	ebiten.Key2: {-4.5, -2.5},
	ebiten.Key3: {-3.5, -2.5},
	ebiten.Key4: {-2.5, -2.5},
	ebiten.Key5: {-1.5, -2.5},
	ebiten.Key6: {-0.5, -2.5},
	ebiten.Key7: {0.5, -2.5},
	ebiten.Key8: {1.5, -2.5},
	ebiten.Key9: {2.5, -2.5},
	ebiten.Key0: {3.5, -2.5},
	// 最上段アルファベット
	ebiten.KeyQ: {-5.25, -1.5},
	ebiten.KeyW: {-4.25, -1.5},
	ebiten.KeyE: {-3.25, -1.5},
	ebiten.KeyR: {-2.25, -1.5},
	ebiten.KeyT: {-1.25, -1.5}, // T is part of TYGH center
	ebiten.KeyY: {-0.25, -1.5}, // Y is part of TYGH center
	ebiten.KeyU: {0.75, -1.5},
	ebiten.KeyI: {1.75, -1.5},
	ebiten.KeyO: {2.75, -1.5},
	ebiten.KeyP: {3.75, -1.5},
	// 中段
	ebiten.KeyA: {-4.75, -0.5},
	ebiten.KeyS: {-3.75, -0.5},
	ebiten.KeyD: {-2.75, -0.5},
	ebiten.KeyF: {-1.75, -0.5},
	ebiten.KeyG: {-0.75, -0.5}, // G is part of TYGH center
	ebiten.KeyH: {0.25, -0.5},  // H is part of TYGH center
	ebiten.KeyJ: {1.25, -0.5},
	ebiten.KeyK: {2.25, -0.5},
	ebiten.KeyL: {3.25, -0.5},
	// 下段
	ebiten.KeyZ: {-4.25, 0.5},
	ebiten.KeyX: {-3.25, 0.5},
	ebiten.KeyC: {-2.25, 0.5},
	ebiten.KeyV: {-1.25, 0.5},
	ebiten.KeyB: {-0.25, 0.5},
	ebiten.KeyN: {0.75, 0.5},
	ebiten.KeyM: {1.75, 0.5},
}

// Player はプレイヤーオブジェクトを表す構造体です
type Player struct {
	pX, pY        float64       // 座標
	vX            float64       // X軸方向の速度
	vY            float64       // Y軸方向の速度
	angle         float64       // 向いている角度（ラジアン）
	width, height int           // プレイヤーの大きさ
	image         *ebiten.Image // プレイヤー画像
	lastKey       ebiten.Key    // 最後に押されたキー
	keyForce      float64       // キー入力による力の強さ
	inertia       float64       // 慣性（0-1の間、小さいほど減速が大きい）
}

// NewPlayer は新しいプレイヤーオブジェクトを作成します
func NewPlayer(x, y float64, img *ebiten.Image) *Player {
	w, h := img.Size()
	return &Player{
		pX:       x,
		pY:       y,
		vX:       0,
		vY:       0,
		angle:    0,
		width:    w,
		height:   h,
		image:    img,
		lastKey:  0,
		keyForce: 1.2,  // キー入力の力の大きさ（調整可能）
		inertia:  0.98, // 慣性（98%の速度を維持）
	}
}

// Update はプレイヤーの状態を更新します
func (p *Player) Update() {
	// 数字キー（1-0）の入力を検出
	for key := ebiten.KeyDigit0; key <= ebiten.KeyDigit9; key++ {
		if inpututil.IsKeyJustPressed(key) {
			// キーが押されたら相対座標を取得
			if pos, ok := keyPositions[key]; ok {
				// 相対座標をベクトルに加算（力を加える）
				p.vX += pos.X * p.keyForce
				p.vY += pos.Y * p.keyForce
				p.lastKey = key
			}
		}
	}

	// A-Zキーの入力を検出
	for key := ebiten.KeyA; key <= ebiten.KeyZ; key++ {
		if inpututil.IsKeyJustPressed(key) {
			// キーが押されたら相対座標を取得
			if pos, ok := keyPositions[key]; ok {
				// 相対座標をベクトルに加算（力を加える）
				p.vX += pos.X * p.keyForce
				p.vY += pos.Y * p.keyForce
				p.lastKey = key
			}
		}
	}

	// 慣性による減速（摩擦）
	p.vX *= p.inertia
	p.vY *= p.inertia

	// 速度が非常に小さい場合は0にする（静止状態）
	if math.Abs(p.vX) < 0.01 {
		p.vX = 0
	}
	if math.Abs(p.vY) < 0.01 {
		p.vY = 0
	}

	// 速度を座標に反映
	p.pX += p.vX
	p.pY += p.vY

	// 移動している場合は向きを更新
	if p.vX != 0 || p.vY != 0 {
		p.angle = math.Atan2(p.vY, p.vX)
	}

	// 画面端の処理（画面外に出ないようにする）
	if p.pX < 0 {
		p.pX = 0
		p.vX *= -0.5 // 跳ね返り
	}
	if p.pX > 640-float64(p.width) {
		p.pX = 640 - float64(p.width)
		p.vX *= -0.5 // 跳ね返り
	}
	if p.pY < 0 {
		p.pY = 0
		p.vY *= -0.5 // 跳ね返り
	}
	if p.pY > 480-float64(p.height) {
		p.pY = 480 - float64(p.height)
		p.vY *= -0.5 // 跳ね返り
	}
}

// Draw はプレイヤーを描画します
func (p *Player) Draw(screen *ebiten.Image) {
	// 画像を使用してプレイヤーを描画
	op := &ebiten.DrawImageOptions{}

	// 画像の中心を回転の中心とするための処理
	op.GeoM.Translate(-float64(p.width)/2, -float64(p.height)/2)

	// 向きに合わせて回転
	op.GeoM.Rotate(p.angle + math.Pi/2) // 回転（上向きが角度0となるよう調整）

	// 座標に配置
	op.GeoM.Translate(p.pX+float64(p.width)/2, p.pY+float64(p.height)/2)

	// 画像を描画
	screen.DrawImage(p.image, op)

	// キーボード相対位置とデバッグ情報を表示
	var lastKeyInfo string
	if p.lastKey != 0 {
		if pos, ok := keyPositions[p.lastKey]; ok {
			lastKeyInfo = fmt.Sprintf("Key: %s, Pos: (%.1f, %.1f)", p.lastKey.String(), pos.X, pos.Y)
		}
	}

	ebitenutil.DebugPrintAt(
		screen,
		fmt.Sprintf("Speed: (%.2f, %.2f)\n%s", p.vX, p.vY, lastKeyInfo),
		int(p.pX), int(p.pY-40),
	)
}

// Game は基本的なゲーム構造体です
type Game struct {
	player          *Player            // プレイヤーオブジェクト
	pressedKeys     map[ebiten.Key]int // 押されたキーとそのエフェクト持続時間
	keyEffectFrames int                // キーが光るエフェクトの持続フレーム数
}

// Update は毎フレーム呼び出されます
func (g *Game) Update() error {
	// 押されたキーの検出とエフェクト時間の更新
	for key := range keyPositions {
		// 新しく押されたキーを検出
		if inpututil.IsKeyJustPressed(key) {
			g.pressedKeys[key] = g.keyEffectFrames
		}

		// 既存のキーエフェクトの持続時間を減らす
		if frames, exists := g.pressedKeys[key]; exists {
			if frames > 0 {
				g.pressedKeys[key]--
			} else {
				delete(g.pressedKeys, key)
			}
		}
	}

	// プレイヤーの状態を更新
	g.player.Update()

	return nil
}

// Draw は毎フレーム呼び出されます
func (g *Game) Draw(screen *ebiten.Image) {
	// 背景を黒で塗りつぶす
	screen.Fill(color.RGBA{40, 40, 40, 255})

	// キーボードレイアウトの表示
	g.drawKeyboardLayout(screen)

	// プレイヤーを描画
	g.player.Draw(screen)

	// 操作説明
	ebitenutil.DebugPrintAt(
		screen,
		"Press A-Z and 1-0 keys to move the character. TYGH is the origin (0,0).",
		10, 10,
	)
}

// キーボードレイアウトの可視化
func (g *Game) drawKeyboardLayout(screen *ebiten.Image) {
	// キー位置のスケールと中心位置
	scale := 30.0
	centerX := 320.0
	centerY := 400.0

	// 各キーを描画
	for key, pos := range keyPositions {
		x := centerX + pos.X*scale
		y := centerY + pos.Y*scale

		// キーの背景色を決定（押されたキーは光る）
		keyColor := color.RGBA{100, 100, 100, 255} // デフォルトの色

		// 押されたキーの場合、光らせる
		if frames, pressed := g.pressedKeys[key]; pressed {
			// フレーム数に応じて輝度を調整（押されたばかりのキーほど明るく）
			brightness := 100 + uint8(155*frames/g.keyEffectFrames)
			keyColor = color.RGBA{brightness, brightness, 0, 255} // 黄色で光る
		}

		// キー背景を描画
		ebitenutil.DrawRect(screen, x-12, y-12, 24, 24, keyColor)

		// キー枠を描画
		borderColor := color.RGBA{160, 160, 160, 255}
		ebitenutil.DrawRect(screen, x-12, y-12, 24, 1, borderColor) // 上辺
		ebitenutil.DrawRect(screen, x-12, y+11, 24, 1, borderColor) // 下辺
		ebitenutil.DrawRect(screen, x-12, y-12, 1, 24, borderColor) // 左辺
		ebitenutil.DrawRect(screen, x+11, y-12, 1, 24, borderColor) // 右辺

		// キー文字
		keyText := key.String()
		// "Key"プレフィックスを削除（ある場合のみ）
		if len(keyText) > 3 && keyText[:3] == "Key" {
			keyText = keyText[3:]
		}
		if len(keyText) > 5 && keyText[:5] == "Digit" {
			keyText = keyText[5:]
		}

		ebitenutil.DebugPrintAt(
			screen,
			keyText,
			int(x-4), int(y-4),
		)
	}

	// 原点（TYGH）を強調
	ebitenutil.DrawRect(screen, centerX, centerY, 10, 10, color.RGBA{255, 0, 0, 255})
}

// Layout はウィンドウサイズに基づいて論理的な画面サイズを返します
func (g *Game) Layout(outsideWidth, outsideHeight int) (screenWidth, screenHeight int) {
	return 640, 480
}

// 画像をロードする関数
func loadImage(path string) (*ebiten.Image, error) {
	// 画像を読み込む
	img, _, err := ebitenutil.NewImageFromFile(path)
	if err != nil {
		return nil, fmt.Errorf("画像をロードできませんでした: %v", err)
	}

	return img, nil
}

func main() {
	// ウィンドウのタイトルを設定
	ebiten.SetWindowTitle("Keyboard Position Game")

	// ウィンドウサイズを設定
	ebiten.SetWindowSize(640, 480)

	// プレイヤー画像をロード
	playerImg, err := loadImage("assets/images/character.png")
	if err != nil {
		log.Fatalf("プレイヤー画像のロードに失敗しました: %v", err)
	}

	// ゲームを作成
	game := &Game{
		player:          NewPlayer(320-15, 240-15, playerImg), // 画面中央にプレイヤーを配置
		pressedKeys:     make(map[ebiten.Key]int),             // 押されたキーのマップを初期化
		keyEffectFrames: 30,                                   // キーエフェクトの持続フレーム数（約0.5秒）
	}

	// ゲームを実行
	if err := ebiten.RunGame(game); err != nil {
		log.Fatal(err)
	}
}
