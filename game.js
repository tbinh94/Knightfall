// game.js
const app = new PIXI.Application({
    width: window.innerWidth,
    height: window.innerHeight,
    backgroundColor: 0x050505,
    resolution: window.devicePixelRatio || 1,
    antialias: true
});

document.getElementById('game-container').appendChild(app.view);

// Fix cursor visibility
app.renderer.view.style.cursor = 'default';

// Game State
const state = {
    worldX: 0,
    player: {
        x: 200,
        y: 0,
        vx: 0,
        vy: 0,
        isGrounded: false,
        speed: 5,
        jumpForce: -15,
        gravity: 0.6
    },
    keys: {}
};

const layers = [];
const layersGroup = new PIXI.Container();
const gameGroup = new PIXI.Container();
app.stage.addChild(layersGroup);
app.stage.addChild(gameGroup);

let playerSprite;
let groundSprite;

// Configuration
const layerConfigs = [
    { file: "Layer_0011_0.png", speed: 0.0 },
    { file: "Layer_0010_1.png", speed: 0.05 },
    { file: "Layer_0009_2.png", speed: 0.1 },
    { file: "Layer_0008_3.png", speed: 0.15 },
    { file: "Layer_0007_Lights.png", speed: 0.15, blend: PIXI.BLEND_MODES.ADD, alpha: 0.4 },
    { file: "Layer_0006_4.png", speed: 0.25 },
    { file: "Layer_0005_5.png", speed: 0.4 },
    { file: "Layer_0004_Lights.png", speed: 0.4, blend: PIXI.BLEND_MODES.ADD, alpha: 0.3 },
    { file: "Layer_0003_6.png", speed: 0.6 },
    { file: "Layer_0002_7.png", speed: 0.8 },
    { file: "Layer_0001_8.png", speed: 0.95 },
    { file: "Layer_0000_9.png", speed: 1.1 }
];

async function init() {
    // 1. Load Backgrounds
    for (const config of layerConfigs) {
        const texture = await PIXI.Assets.load(`assets/backgrounds/${config.file}`);
        const tilingSprite = new PIXI.TilingSprite(texture, app.screen.width, app.screen.height);
        const scale = app.screen.height / texture.height;
        tilingSprite.tileScale.set(scale);
        if (config.blend) {
            tilingSprite.blendMode = config.blend;
            tilingSprite.alpha = config.alpha || 0.6;
        }
        layersGroup.addChild(tilingSprite);
        layers.push({ sprite: tilingSprite, speed: config.speed });
    }

    // 2. Load Ground
    const tilesetTexture = await PIXI.Assets.load('assets/tilesets/medieval_tileset.png');
    // Extract a dark ground tile (e.g., Row 0, Col 1)
    const tileSize = 16;
    const groundRect = new PIXI.Rectangle(tileSize * 1, 0, tileSize, tileSize);
    const groundTileTexture = new PIXI.Texture(tilesetTexture.baseTexture, groundRect);
    
    const groundHeight = 60;
    groundSprite = new PIXI.TilingSprite(groundTileTexture, app.screen.width, groundHeight);
    groundSprite.y = app.screen.height - groundHeight;
    groundSprite.tileScale.set(groundHeight / tileSize);
    gameGroup.addChild(groundSprite);

    // 3. Load Player
    const runSheet = await PIXI.Assets.load('assets/player/Run.png');
    const idleSheet = await PIXI.Assets.load('assets/player/Idle.png');
    
    const frameW = 128;
    const frameH = 64;
    
    const extractFrames = (texture, count) => {
        const frames = [];
        for (let i = 0; i < count; i++) {
            const rect = new PIXI.Rectangle(i * frameW, 0, frameW, frameH);
            frames.push(new PIXI.Texture(texture.baseTexture, rect));
        }
        return frames;
    };

    const runFrames = extractFrames(runSheet, 8);
    const idleFrames = extractFrames(idleSheet, 8);
    
    state.animations = {
        run: runFrames,
        idle: idleFrames
    };

    playerSprite = new PIXI.AnimatedSprite(state.animations.idle);

    playerSprite.anchor.set(0.5, 1);
    playerSprite.animationSpeed = 0.15;
    playerSprite.scale.set(3);
    playerSprite.x = state.player.x;
    playerSprite.y = groundSprite.y;
    playerSprite.play();
    gameGroup.addChild(playerSprite);

    state.player.y = groundSprite.y;

    // 4. Input Handling
    window.addEventListener('keydown', e => state.keys[e.code] = true);
    window.addEventListener('keyup', e => state.keys[e.code] = false);

    // 5. Game Loop
    app.ticker.add((delta) => {
        updatePlayer(delta);
        updateCamera(delta);
    });
}

function updatePlayer(delta) {
    const p = state.player;
    
    // Horizontal movement
    let moveDir = 0;
    if (state.keys['ArrowRight'] || state.keys['KeyD']) moveDir = 1;
    if (state.keys['ArrowLeft'] || state.keys['KeyA']) moveDir = -1;

    p.vx = moveDir * p.speed;
    
    // Jump
    if ((state.keys['ArrowUp'] || state.keys['KeyW'] || state.keys['Space']) && p.isGrounded) {
        p.vy = p.jumpForce;
        p.isGrounded = false;
    }

    // Apply Gravity
    p.vy += p.gravity * delta;
    p.y += p.vy * delta;

    // Ground Collision
    const groundY = groundSprite.y;
    if (p.y >= groundY) {
        p.y = groundY;
        p.vy = 0;
        p.isGrounded = true;
    }

    // Update Sprite
    playerSprite.y = p.y;
    
    // Update Sprite Animation
    if (Math.abs(p.vx) > 0.1) {
        playerSprite.scale.x = (p.vx > 0 ? 1 : -1) * Math.abs(playerSprite.scale.x);
        if (playerSprite.textures !== state.animations.run) {
            playerSprite.textures = state.animations.run;
            playerSprite.play();
        }
    } else {
        if (playerSprite.textures !== state.animations.idle) {
            playerSprite.textures = state.animations.idle;
            playerSprite.play();
        }
    }

    if (!p.isGrounded) {
        // Simple jump pose logic could go here
    }

}

function updateCamera(delta) {
    const p = state.player;
    
    // In a side-scroller, the player stays mostly in the middle
    // and the world moves around them.
    // We'll keep it simple: player moves, and we shift the worldX offset.
    
    state.worldX += p.vx * delta;
    
    // Tile Backgrounds
    layers.forEach(layer => {
        layer.sprite.tilePosition.x = -(state.worldX * layer.speed);
    });

    // Tile Ground
    groundSprite.tilePosition.x = -state.worldX;
}

// Handle Window Resize
window.addEventListener('resize', () => {
    app.renderer.resize(window.innerWidth, window.innerHeight);
    layers.forEach(layer => {
        layer.sprite.width = app.screen.width;
        layer.sprite.height = app.screen.height;
        layer.sprite.tileScale.set(app.screen.height / layer.sprite.texture.height);
    });
    groundSprite.width = app.screen.width;
    groundSprite.y = app.screen.height - groundSprite.height;
});

init();
