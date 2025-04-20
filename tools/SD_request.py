## localhost:7860 に automatic1111/stable-diffusion-webui が立ち上がっているので、そこにプロンプトを送り込んで、画像をダウンロードしてくる

import requests
import io
import base64
from PIL import Image
import os
import json
import time
import subprocess
import sys
from datetime import datetime
import argparse

# Global API base URL - can be changed if needed (e.g., for remote servers)
API_BASE_URL = "http://localhost:7860/sdapi/v1"

# WebUIを起動するバッチファイルのデフォルトパス（必要に応じて変更してください）
DEFAULT_WEBUI_BATCH_PATH = r"C:\Users\shinta\Desktop\automatic\automatic\run.bat"

def is_webui_running(api_url=None, timeout=5):
    """
    Stable Diffusion WebUI APIが応答するかどうかをチェックします

    Args:
        api_url (str, optional): チェックするAPIエンドポイント。Noneの場合はAPIのモデル一覧エンドポイントを使用
        timeout (int): タイムアウト秒数

    Returns:
        bool: WebUIが起動していればTrue、そうでなければFalse
    """
    if api_url is None:
        api_url = f"{API_BASE_URL}/sd-models"

    try:
        response = requests.get(api_url, timeout=timeout)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def start_webui(batch_path=DEFAULT_WEBUI_BATCH_PATH, wait_time=30):
    """
    Stable Diffusion WebUIをバッチファイルから起動します

    Args:
        batch_path (str): 起動用バッチファイルのパス
        wait_time (int): 起動を待機する最大時間（秒）

    Returns:
        bool: 起動に成功したかどうか
    """
    if not os.path.exists(batch_path):
        print(f"エラー: 指定されたバッチファイルが見つかりません: {batch_path}")
        return False

    print(f"Stable Diffusion WebUIを起動しています: {batch_path}")

    # バッチファイルのディレクトリを取得
    batch_dir = os.path.dirname(batch_path)

    # バッチファイルをサブプロセスとして起動（非同期）
    try:
        # 1. まず新しいコマンドプロンプトウィンドウを使う方法を試す
        print("方法1: コマンドプロンプト経由で起動を試みます...")
        cmd = f'start cmd /K "cd /d "{batch_dir}" && "{batch_path}""'
        process = subprocess.Popen(cmd, shell=True)

        # WebUIの起動を待機
        print(f"WebUIの起動を待機しています（最大{wait_time}秒）...")
        for i in range(wait_time):
            if is_webui_running():
                print(f"WebUIの起動を確認しました！（{i+1}秒経過）")
                return True

            # 1秒待機して再チェック
            time.sleep(1)
            if (i + 1) % 5 == 0:
                print(f"まだ起動中...（{i+1}秒経過）")

        # 最初の方法で起動しなかった場合、別の方法を試す
        print("方法1で起動できませんでした。方法2を試みます...")

        # 2. cwd引数を使用してカレントディレクトリを設定
        print("方法2: カレントディレクトリを設定して起動を試みます...")
        process = subprocess.Popen(
            batch_path,
            cwd=batch_dir,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            shell=True
        )

        # 再びWebUIの起動を待機
        print(f"WebUIの起動を待機しています（最大{wait_time}秒）...")
        for i in range(wait_time):
            if is_webui_running():
                print(f"WebUIの起動を確認しました！（{i+1}秒経過）")
                return True

            # 1秒待機して再チェック
            time.sleep(1)
            if (i + 1) % 5 == 0:
                print(f"まだ起動中...（{i+1}秒経過）")

        # それでも起動しなかった場合、詳細なデバッグ情報を表示
        print(f"タイムアウト: {wait_time}秒経過してもWebUIが応答しません")
        print("デバッグ情報:")
        print(f"- バッチファイルパス: {batch_path}")
        print(f"- バッチファイルディレクトリ: {batch_dir}")
        print(f"- ファイルの存在確認: {'存在します' if os.path.exists(batch_path) else '存在しません'}")
        print(f"- ファイルサイズ: {os.path.getsize(batch_path) if os.path.exists(batch_path) else 'N/A'} バイト")

        # バッチファイルの内容を確認（デバッグ用）
        if os.path.exists(batch_path):
            try:
                with open(batch_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(500)  # 最初の500文字だけ読み込む
                print(f"- バッチファイルの内容（先頭部分）:\n{content}...")
            except Exception as e:
                print(f"- バッチファイルの読み込みに失敗: {str(e)}")

        return False

    except Exception as e:
        print(f"WebUIの起動中にエラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()  # スタックトレースを表示
        return False


def ensure_webui_is_running(batch_path=DEFAULT_WEBUI_BATCH_PATH, wait_time=30):
    """
    WebUIが実行中であることを確認し、実行されていなければ起動します

    Args:
        batch_path (str): 起動用バッチファイルのパス
        wait_time (int): 起動を待機する最大時間（秒）

    Returns:
        bool: WebUIが起動しているかどうか
    """
    print("Stable Diffusion WebUIの起動状態を確認しています...")

    if is_webui_running():
        print("Stable Diffusion WebUIは既に起動しています")
        return True

    print("Stable Diffusion WebUIは起動していません")
    return start_webui(batch_path, wait_time)


def get_available_models():
    """
    Get a list of available models from Stable Diffusion WebUI.

    Returns:
        dict: Dictionary with model information including:
            - 'current_model': Currently loaded model name
            - 'model_list': List of available model names
            - 'model_info': Detailed info about each model if available
    """
    url = f"{API_BASE_URL}/sd-models"

    try:
        print("Fetching available models from Stable Diffusion WebUI...")
        response = requests.get(url)

        if response.status_code != 200:
            print(f"Error: Received status code {response.status_code}")
            print(response.text)
            return {'current_model': None, 'model_list': [], 'model_info': {}}

        models_data = response.json()
        model_list = [model_data['title'] for model_data in models_data]

        # Get current model info
        current_model = None
        try:
            options_response = requests.get(f"{API_BASE_URL}/options")
            if options_response.status_code == 200:
                options = options_response.json()
                current_model = options.get('sd_model_checkpoint')
        except Exception as e:
            print(f"Warning: Could not get current model info: {str(e)}")

        # Create a more detailed model info dictionary
        model_info = {}
        for model_data in models_data:
            model_info[model_data['title']] = {
                'filename': model_data.get('filename', ''),
                'hash': model_data.get('hash', ''),
                'model_name': model_data.get('model_name', ''),
                'config': model_data.get('config', '')
            }

        print(f"Found {len(model_list)} models. Currently loaded: {current_model}")
        return {
            'current_model': current_model,
            'model_list': model_list,
            'model_info': model_info
        }

    except Exception as e:
        print(f"Error fetching models: {str(e)}")
        return {'current_model': None, 'model_list': [], 'model_info': {}}


def set_model(model_name):
    """
    Set the current Stable Diffusion model.

    Args:
        model_name (str): The name of the model to load

    Returns:
        bool: True if successful, False otherwise
    """
    url = f"{API_BASE_URL}/options"

    payload = {
        "sd_model_checkpoint": model_name
    }

    try:
        print(f"Setting model to: {model_name}...")
        response = requests.post(url, json=payload)

        if response.status_code != 200:
            print(f"Error: Received status code {response.status_code}")
            print(response.text)
            return False

        print(f"Successfully changed model to: {model_name}")
        return True

    except Exception as e:
        print(f"Error changing model: {str(e)}")
        return False


def send_sd_request(positive_prompt, negative_prompt, output_dir="output", filename=None,
                    steps=20, width=512, height=768, cfg_scale=7, sampler="DPM++ 2M Karras",
                    batch_size=1, batch_count=1, seed=-1, model=None, save_metadata=False, auto_start_webui=True,
                    webui_batch_path=DEFAULT_WEBUI_BATCH_PATH, wait_time=30):
    """
    Send request to Stable Diffusion WebUI API and save the generated images.

    Args:
        positive_prompt (str): The positive prompt for image generation
        negative_prompt (str): The negative prompt to avoid certain elements
        output_dir (str): Directory to save the generated images
        filename (str, optional): Base filename for the images. If None, uses timestamp.
        steps (int): Number of sampling steps
        width (int): Image width
        height (int): Image height
        cfg_scale (float): CFG scale (guidance scale)
        sampler (str): Sampler name
        batch_size (int): Number of images in a batch
        batch_count (int): Number of batches to generate
        seed (int): Seed for reproducible image generation. Default is -1 (random).
        model (str, optional): Model name to use for generation. If provided, will switch to this model first.
        save_metadata (bool): Whether to save the API response and metadata as JSON
        auto_start_webui (bool): Whether to automatically start WebUI if it's not running
        webui_batch_path (str): Path to the WebUI startup batch file
        wait_time (int): How many seconds to wait for WebUI to start

    Returns:
        tuple: (saved_paths, output_dir) - 生成された画像のパスリストと出力ディレクトリ
    """
    # WebUIが起動しているか確認し、必要であれば起動
    if auto_start_webui and not is_webui_running():
        print("Stable Diffusion WebUIが起動していません。自動的に起動を試みます...")
        if not ensure_webui_is_running(webui_batch_path, wait_time):
            print("エラー: WebUIを起動できませんでした。リクエストを中止します。")
            return ([], output_dir)

    # Change model if requested
    if model:
        model_changed = set_model(model)
        if not model_changed:
            print(f"Warning: Could not change to model '{model}'. Using current model instead.")

    url = f"{API_BASE_URL}/txt2img"

    payload = {
        "prompt": positive_prompt,
        "negative_prompt": negative_prompt,
        "steps": steps,
        "width": width,
        "height": height,
        "cfg_scale": cfg_scale,
        "sampler_name": sampler,
        "batch_size": batch_size,
        "n_iter": batch_count,
        "seed": seed,  # シード値をペイロードに明示的に追加
    }

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Generate filename based on timestamp if not provided
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sd_generated_{timestamp}"

    try:
        print(f"Sending request to Stable Diffusion WebUI with prompt: {positive_prompt[:50]}...")
        response = requests.post(url, json=payload)

        if response.status_code != 200:
            print(f"Error: Received status code {response.status_code}")
            print(response.text)
            return ([], output_dir)

        r = response.json()
        saved_paths = []

        # Process and save images
        for i, img_b64 in enumerate(r['images']):
            image_data = base64.b64decode(img_b64.split(",", 1)[0] if "," in img_b64 else img_b64)
            image = Image.open(io.BytesIO(image_data))

            # Save the image
            img_filename = f"{filename}_{i+1}.png"
            img_path = os.path.join(output_dir, img_filename)
            image.save(img_path)
            saved_paths.append(img_path)
            print(f"Saved image to {img_path}")

            # JSONメタデータを保存する機能は無効化（必要な場合のみ使用）
            if save_metadata:
                # ログディレクトリの作成 (メタデータJSONファイル用)
                log_dir = os.path.join(output_dir, "logs")
                os.makedirs(log_dir, exist_ok=True)

                # 画像情報を含むメタデータを作成
                metadata = {
                    "timestamp": datetime.now().isoformat(),
                    "request": {
                        "prompt": positive_prompt,
                        "negative_prompt": negative_prompt,
                        "steps": steps,
                        "width": width,
                        "height": height,
                        "cfg_scale": cfg_scale,
                        "sampler": sampler,
                        "batch_size": batch_size,
                        "batch_count": batch_count,
                        "model": model
                    },
                    "image_path": img_path,
                    "seed": r.get("seeds", [None])[i] if "seeds" in r else None,
                    "info": r.get("info", "")
                }

                # レスポンスから画像データを除外して保存（サイズが大きいため）
                response_copy = r.copy()
                if "images" in response_copy:
                    # 画像データを含まないようにする（サイズが大きすぎるため）
                    response_copy["images"] = [f"<image_data_removed_{j+1}>" for j in range(len(response_copy["images"]))]

                metadata["api_response"] = response_copy

                # メタデータをJSONファイルとして保存
                json_filename = f"{filename}_{i+1}_metadata.json"
                json_path = os.path.join(log_dir, json_filename)
                with open(json_path, 'w', encoding='utf-8') as json_file:
                    json.dump(metadata, json_file, indent=2, ensure_ascii=False)

                print(f"Saved metadata to {json_path}")

        if saved_paths:
            print(f"Successfully generated {len(saved_paths)} images.")
        else:
            print("No images were generated.")

        return (saved_paths, output_dir)

    except Exception as e:
        print(f"Error in SD request: {str(e)}")
        return ([], output_dir)


def send_img2img_request(input_image_path, positive_prompt, negative_prompt="", output_dir="output", filename=None,
                       steps=20, width=None, height=None, cfg_scale=7, sampler="DPM++ 2M Karras",
                       denoising_strength=0.75, resize_mode=0, batch_size=1, batch_count=1, seed=-1,
                       model=None, save_metadata=False, auto_start_webui=True,
                       webui_batch_path=DEFAULT_WEBUI_BATCH_PATH, wait_time=30):
    """
    Send image-to-image request to Stable Diffusion WebUI API and save the generated images.

    Args:
        input_image_path (str): Path to the input image to transform
        positive_prompt (str): The positive prompt for image generation
        negative_prompt (str): The negative prompt to avoid certain elements
        output_dir (str): Directory to save the generated images
        filename (str, optional): Base filename for the images. If None, uses timestamp.
        steps (int): Number of sampling steps
        width (int, optional): Output image width. If None, uses input image width.
        height (int, optional): Output image height. If None, uses input image height.
        cfg_scale (float): CFG scale (guidance scale)
        sampler (str): Sampler name
        denoising_strength (float): How much to transform the image (0.0 to 1.0)
        resize_mode (int): Resize mode (0: Just resize, 1: Crop and resize, 2: Resize and fill)
        batch_size (int): Number of images in a batch
        batch_count (int): Number of batches to generate
        seed (int): Seed for reproducible image generation. Default is -1 (random).
        model (str, optional): Model name to use for generation. If provided, will switch to this model first.
        save_metadata (bool): Whether to save the API response and metadata as JSON
        auto_start_webui (bool): Whether to automatically start WebUI if it's not running
        webui_batch_path (str): Path to the WebUI startup batch file
        wait_time (int): How many seconds to wait for WebUI to start

    Returns:
        tuple: (saved_paths, output_dir) - List of paths to generated images and output directory
    """
    # WebUIが起動しているか確認し、必要であれば起動
    if auto_start_webui and not is_webui_running():
        print("Stable Diffusion WebUIが起動していません。自動的に起動を試みます...")
        if not ensure_webui_is_running(webui_batch_path, wait_time):
            print("エラー: WebUIを起動できませんでした。リクエストを中止します。")
            return ([], output_dir)

    # Change model if requested
    if model:
        model_changed = set_model(model)
        if not model_changed:
            print(f"Warning: Could not change to model '{model}'. Using current model instead.")

    # Check if input image exists
    if not os.path.isfile(input_image_path):
        print(f"Error: Input image not found at {input_image_path}")
        return ([], output_dir)

    # Read and encode the input image
    try:
        with Image.open(input_image_path) as img:
            # Get original dimensions if width/height not specified
            orig_width, orig_height = img.size
            if width is None:
                width = orig_width
            if height is None:
                height = orig_height

            # Convert image to base64
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"Error reading input image: {str(e)}")
        return ([], output_dir)

    url = f"{API_BASE_URL}/img2img"

    payload = {
        "init_images": [img_base64],
        "prompt": positive_prompt,
        "negative_prompt": negative_prompt,
        "steps": steps,
        "width": width,
        "height": height,
        "cfg_scale": cfg_scale,
        "sampler_name": sampler,
        "denoising_strength": denoising_strength,
        "resize_mode": resize_mode,
        "batch_size": batch_size,
        "n_iter": batch_count,
        "seed": seed,  # シード値を追加
    }

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Generate filename based on timestamp if not provided
    if filename is None:
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        input_name = os.path.splitext(os.path.basename(input_image_path))[0]
        filename = f"{input_name}_i2i_{timestamp}_{int(time.time()*1000) % 10000000}"

    try:
        print(f"Sending image-to-image request to Stable Diffusion WebUI...")
        response = requests.post(url, json=payload)

        if response.status_code != 200:
            print(f"Error: Received status code {response.status_code}")
            print(response.text)
            return ([], output_dir)

        r = response.json()
        saved_paths = []

        # Process and save images
        for i, img_b64 in enumerate(r['images']):
            image_data = base64.b64decode(img_b64.split(",", 1)[0] if "," in img_b64 else img_b64)
            image = Image.open(io.BytesIO(image_data))

            # Save the image
            img_filename = f"{filename}_{i+1}.png"
            img_path = os.path.join(output_dir, img_filename)
            image.save(img_path)
            saved_paths.append(img_path)
            print(f"Saved image to {img_path}")

            # Save metadata if requested
            if save_metadata:
                # ログディレクトリの作成 (メタデータJSONファイル用)
                log_dir = os.path.join(output_dir, "logs")
                os.makedirs(log_dir, exist_ok=True)

                # 画像情報を含むメタデータを作成
                metadata = {
                    "timestamp": datetime.now().isoformat(),
                    "request": {
                        "input_image": input_image_path,
                        "prompt": positive_prompt,
                        "negative_prompt": negative_prompt,
                        "steps": steps,
                        "width": width,
                        "height": height,
                        "cfg_scale": cfg_scale,
                        "sampler": sampler,
                        "denoising_strength": denoising_strength,
                        "resize_mode": resize_mode,
                        "batch_size": batch_size,
                        "batch_count": batch_count,
                        "model": model
                    },
                    "image_path": img_path,
                    "seed": r.get("seeds", [None])[i] if "seeds" in r else None,
                    "info": r.get("info", "")
                }

                # レスポンスから画像データを除外して保存（サイズが大きいため）
                response_copy = r.copy()
                if "images" in response_copy:
                    # 画像データを含まないようにする（サイズが大きすぎるため）
                    response_copy["images"] = [f"<image_data_removed_{j+1}>" for j in range(len(response_copy["images"]))]

                metadata["api_response"] = response_copy

                # メタデータをJSONファイルとして保存
                json_filename = f"{filename}_{i+1}_metadata.json"
                json_path = os.path.join(log_dir, json_filename)
                with open(json_path, 'w', encoding='utf-8') as json_file:
                    json.dump(metadata, json_file, indent=2, ensure_ascii=False)

                print(f"Saved metadata to {json_path}")

        if saved_paths:
            print(f"Successfully generated {len(saved_paths)} images.")
        else:
            print("No images were generated.")

        return (saved_paths, output_dir)

    except Exception as e:
        print(f"Error in img2img request: {str(e)}")
        import traceback
        traceback.print_exc()
        return ([], output_dir)

def main():
    global API_BASE_URL

    parser = argparse.ArgumentParser(description='Send requests to Stable Diffusion WebUI')
    parser.add_argument('--positive', help='Positive prompt')
    parser.add_argument('--negative', default='', help='Negative prompt')
    parser.add_argument('--output', default='output', help='Output directory')
    parser.add_argument('--filename', help='Base filename for output images')
    parser.add_argument('--steps', type=int, default=20, help='Number of sampling steps')
    parser.add_argument('--width', type=int, default=512, help='Image width')
    parser.add_argument('--height', type=int, default=768, help='Image height')
    parser.add_argument('--cfg_scale', type=float, default=7.0, help='CFG scale')
    parser.add_argument('--sampler', default='DPM++ 2M Karras', help='Sampler name')
    parser.add_argument('--batch_size', type=int, default=1, help='Batch size')
    parser.add_argument('--batch_count', type=int, default=1, help='Batch count')
    parser.add_argument('--model', help='Model name to use for generation')
    parser.add_argument('--list-models', action='store_true', help='List available models and exit')
    parser.add_argument('--api-url', help=f'API base URL (default: {API_BASE_URL})')
    parser.add_argument('--auto-start', action='store_true', help='自動的にWebUIを起動（必要な場合）')
    parser.add_argument('--webui-path', help=f'WebUI起動用バッチファイルのパス (default: {DEFAULT_WEBUI_BATCH_PATH})')
    parser.add_argument('--wait-time', type=int, default=30, help='WebUI起動待機時間（秒）')
    parser.add_argument('--check-only', action='store_true', help='WebUIの起動状態のみを確認して終了')

    # img2img specific arguments
    parser.add_argument('--img2img', action='store_true', help='Use image-to-image mode instead of text-to-image')
    parser.add_argument('--input-image', help='Input image path for img2img mode')
    parser.add_argument('--denoising-strength', type=float, default=0.75, help='Denoising strength for img2img (0.0 to 1.0)')
    parser.add_argument('--resize-mode', type=int, default=0, help='Resize mode: 0=Just resize, 1=Crop and resize, 2=Resize and fill')

    args = parser.parse_args()

    # Update base URL if provided
    if args.api_url:
        API_BASE_URL = args.api_url
        print(f"Using custom API URL: {API_BASE_URL}")

    # WebUIの起動確認のみ行う場合
    if args.check_only:
        webui_path = args.webui_path if args.webui_path else DEFAULT_WEBUI_BATCH_PATH
        if args.auto_start:
            if ensure_webui_is_running(webui_path, args.wait_time):
                print("Stable Diffusion WebUIの準備が整いました！APIリクエストを送信できます")
                sys.exit(0)
            else:
                print("Stable Diffusion WebUIを起動できませんでした")
                sys.exit(1)
        else:
            if is_webui_running():
                print("Stable Diffusion WebUIは起動しています")
                sys.exit(0)
            else:
                print("Stable Diffusion WebUIは起動していません")
                sys.exit(1)

    # WebUIが起動しているか確認（auto-startフラグが立っている場合は自動起動を試みる）
    if args.auto_start:
        webui_path = args.webui_path if args.webui_path else DEFAULT_WEBUI_BATCH_PATH
        if not ensure_webui_is_running(webui_path, args.wait_time):
            print("Stable Diffusion WebUIを起動できませんでした。処理を中止します。")
            sys.exit(1)

    # If --list-models is specified, show available models and exit
    if args.list_models:
        models = get_available_models()
        print("\nAvailable models:")
        print("-" * 50)
        for i, model_name in enumerate(models['model_list'], 1):
            current = " (current)" if model_name == models['current_model'] else ""
            print(f"{i}. {model_name}{current}")
        print("-" * 50)
        return

    # img2imgモードの場合
    if args.img2img:
        if not args.input_image:
            print("エラー: img2imgモードでは --input-image パラメータが必要です")
            parser.print_help()
            sys.exit(1)

        if not args.positive:
            print("エラー: img2imgモードでも --positive プロンプトが必要です")
            parser.print_help()
            sys.exit(1)

        # Image to Imageリクエストを送信
        send_img2img_request(
            input_image_path=args.input_image,
            positive_prompt=args.positive,
            negative_prompt=args.negative,
            output_dir=args.output,
            filename=args.filename,
            steps=args.steps,
            width=args.width,
            height=args.height,
            cfg_scale=args.cfg_scale,
            sampler=args.sampler,
            denoising_strength=args.denoising_strength,
            resize_mode=args.resize_mode,
            batch_size=args.batch_size,
            batch_count=args.batch_count,
            model=args.model,
            auto_start_webui=args.auto_start,
            webui_batch_path=args.webui_path if args.webui_path else DEFAULT_WEBUI_BATCH_PATH,
            wait_time=args.wait_time
        )
    # txt2imgモードの場合（デフォルト）
    else:
        # 画像生成の場合は --positive が必須
        if not args.positive:
            print("エラー: 画像生成には --positive 引数が必要です")
            parser.print_help()
            sys.exit(1)

        send_sd_request(
            positive_prompt=args.positive,
            negative_prompt=args.negative,
            output_dir=args.output,
            filename=args.filename,
            steps=args.steps,
            width=args.width,
            height=args.height,
            cfg_scale=args.cfg_scale,
            sampler=args.sampler,
            batch_size=args.batch_size,
            batch_count=args.batch_count,
            model=args.model,
            auto_start_webui=args.auto_start,
            webui_batch_path=args.webui_path if args.webui_path else DEFAULT_WEBUI_BATCH_PATH,
            wait_time=args.wait_time
        )

if __name__ == "__main__":
    main()

