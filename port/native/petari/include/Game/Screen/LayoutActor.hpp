#pragma once

#include "Game/NameObj/NameObj.hpp"
#include "Game/Screen/LayoutActorFlag.hpp"
#include <nebula_geometry.hpp>

class EffectSystem;
class LayoutManager;
class Nerve;
class PaneEffectKeeper;
class Spine;
class StarPointerLayoutTargetKeeper;

class LayoutActor : public NameObj {
public:
    LayoutActor(const char*, bool);

    virtual ~LayoutActor() override {
    }

    virtual void movement() override;
    virtual void draw() const override;
    virtual void calcAnim() override;
    virtual void appear();
    virtual void kill();

    virtual void control() {
    }

    void setNerve(const Nerve*) const;
    bool isNerve(const Nerve*) const;
    // The authored step (1/60 s) the nerve is in (the fixed tick: ticks / k, docs/fixed-tick.md).
    s32 getNerveStep() const;
    // The nerve's counter in ticks.
    s32 getNerveTick() const;
    Vec2f getTrans() const;
    void setTrans(const Vec2f&);
    LayoutManager* getLayoutManager() const;
    void createPaneMtxRef(const char*);
    MtxPtr getPaneMtxRef(const char*);
    void initLayoutManager(const char*, u32);
    void initLayoutManagerNoConvertFilename(const char*, u32);
    void initLayoutManagerWithTextBoxBufferLength(const char*, u32, u32);
    // As initLayoutManager, but a text box with no message stays as its layout file made it (a mod's own layout).
    void initLayoutManagerKeepText(const char*, u32);
    void initNerve(const Nerve*);
    void initEffectKeeper(int, const char*, const EffectSystem*);
    void initPointingTarget(int);
    void updateSpine();

    LayoutManager* mLayoutManager;
    Spine* mSpine;
    PaneEffectKeeper* mEffectKeeper;
    StarPointerLayoutTargetKeeper* mPointingTarget;
    LayoutActorFlag mFlag;
};
